#!/usr/bin/env python3
"""Small, standard-library-only KakaoTalk "send to me" client."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import stat
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
DEFAULT_DIR = Path.home() / ".config" / "economic-news-card" / "kakao"
REPO_ROOT = Path(__file__).resolve().parents[2]


class KakaoError(RuntimeError):
    pass


class KakaoRejectedError(KakaoError):
    """A 4xx response confirms that Kakao rejected the request."""


class KakaoUncertainError(KakaoError):
    """Delivery cannot be determined from a transport or server failure."""


def _private_json_write(path: Path, value: object) -> None:
    path = path.expanduser().resolve()
    if path == REPO_ROOT or REPO_ROOT in path.parents:
        raise KakaoError(f"Private state must be outside the Git repository: {path}")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path, *, required: bool = True) -> dict:
    try:
        with path.expanduser().open(encoding="utf-8") as stream:
            value = json.load(stream)
    except FileNotFoundError:
        if required:
            raise KakaoError(f"Missing file: {path}") from None
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise KakaoError(f"Cannot read valid JSON from {path}: {type(exc).__name__}") from None
    if not isinstance(value, dict):
        raise KakaoError(f"Expected a JSON object in {path}")
    return value


def load_config(path: Path) -> dict:
    config = _read_json(path, required=False)
    env = os.environ
    client_id = env.get("KAKAO_REST_API_KEY") or config.get("client_id")
    client_secret = env.get("KAKAO_CLIENT_SECRET") or config.get("client_secret")
    if not client_id:
        raise KakaoError("Set KAKAO_REST_API_KEY or config.client_id")
    if config.get("client_secret"):
        mode = stat.S_IMODE(path.expanduser().stat().st_mode)
        if mode & 0o077:
            raise KakaoError(f"Config containing client_secret must have mode 0600: {path}")
    return {
        "client_id": str(client_id),
        "client_secret": str(client_secret) if client_secret else None,
        "redirect_uri": str(config.get("redirect_uri", "http://127.0.0.1:8765/callback")),
        "token_path": Path(config.get("token_path", DEFAULT_DIR / "tokens.json")).expanduser(),
        "receipt_path": Path(config.get("receipt_path", DEFAULT_DIR / "receipts.json")).expanduser(),
        "lock_path": Path(config.get("lock_path", DEFAULT_DIR / "state.lock")).expanduser(),
        "request_timeout": float(config.get("request_timeout", 15)),
    }


@contextlib.contextmanager
def _state_lock(config: dict):
    path = Path(config.get("lock_path") or config["receipt_path"].with_name("state.lock")).expanduser().resolve()
    if path == REPO_ROOT or REPO_ROOT in path.parents:
        raise KakaoError(f"Private state must be outside the Git repository: {path}")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.chmod(path, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _post_json(url: str, fields: dict, *, token: str | None, timeout: float) -> dict:
    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=urlencode(fields).encode(), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        if 500 <= exc.code <= 599:
            raise KakaoUncertainError(
                f"Kakao API response was not confirmed (HTTP {exc.code} server error)"
            ) from None
        raise KakaoRejectedError(
            f"Kakao API rejected the request (HTTP {exc.code}); inspect app settings and permissions"
        ) from None
    except (URLError, TimeoutError, OSError):
        raise KakaoUncertainError("Kakao API response was not confirmed (network error or timeout)") from None
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise KakaoError("Kakao API returned an invalid response") from None
    if not isinstance(value, dict):
        raise KakaoError("Kakao API returned an invalid response")
    return value


def _merge_token(old: dict, new: dict) -> dict:
    if not new.get("access_token"):
        raise KakaoError("Token response did not contain an access token")
    merged = dict(old)
    merged.update(new)
    merged["obtained_at"] = int(time.time())
    merged["expires_at"] = int(time.time()) + int(new.get("expires_in", 0))
    return merged


def _refresh_unlocked(config: dict, token: dict) -> dict:
    if not token.get("refresh_token"):
        raise KakaoError("No refresh token; run authorize again")
    fields = {
        "grant_type": "refresh_token",
        "client_id": config["client_id"],
        "refresh_token": token["refresh_token"],
    }
    if config["client_secret"]:
        fields["client_secret"] = config["client_secret"]
    renewed = _post_json(TOKEN_URL, fields, token=None, timeout=config["request_timeout"])
    merged = _merge_token(token, renewed)
    _private_json_write(config["token_path"], merged)
    return merged


def refresh(config: dict, token: dict) -> dict:
    with _state_lock(config):
        return _refresh_unlocked(config, token)


def access_token(config: dict, *, state_locked: bool = False) -> str:
    token = _read_json(config["token_path"])
    if int(token.get("expires_at", 0)) <= int(time.time()) + 60:
        token = _refresh_unlocked(config, token) if state_locked else refresh(config, token)
    value = token.get("access_token")
    if not value:
        raise KakaoError("Token file has no access token; run authorize")
    return str(value)


def _parse_oauth_callback(path: str, expected_state: str) -> tuple[int, dict[str, str], bytes]:
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    if parsed.path != "/callback" or not hmac.compare_digest(query.get("state", [""])[0], expected_state):
        return 400, {}, b"Invalid OAuth state. Return to the terminal."
    if query.get("error"):
        return 400, {"error": "Authorization was denied"}, b"Authorization was denied. Return to the terminal."
    if query.get("code", [""])[0]:
        return 200, {"code": query["code"][0]}, b"Authorization received. You can close this tab."
    return 400, {"error": "Authorization response had no code"}, b"Missing authorization code. Return to the terminal."


def authorize(config: dict, wait_seconds: int) -> None:
    parsed = urlparse(config["redirect_uri"])
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path != "/callback" or not parsed.port:
        raise KakaoError("redirect_uri must be http://127.0.0.1:<port>/callback")
    state = secrets.token_urlsafe(32)
    result: dict[str, str] = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            status_code, callback_result, body = _parse_oauth_callback(self.path, state)
            result.update(callback_result)
            self.send_response(status_code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *args: object) -> None:
            return

    params = {
        "response_type": "code",
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "scope": "talk_message",
        "state": state,
    }
    server = HTTPServer(("127.0.0.1", parsed.port), Callback)
    server.timeout = wait_seconds
    print("Open this Kakao authorization URL in your browser:", flush=True)
    print(f"{AUTH_URL}?{urlencode(params)}", flush=True)
    server.handle_request()
    server.server_close()
    if "code" not in result:
        raise KakaoError(result.get("error", "Authorization timed out or callback state was invalid"))
    fields = {
        "grant_type": "authorization_code",
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "code": result["code"],
    }
    if config["client_secret"]:
        fields["client_secret"] = config["client_secret"]
    issued = _post_json(TOKEN_URL, fields, token=None, timeout=config["request_timeout"])
    with _state_lock(config):
        _private_json_write(config["token_path"], _merge_token({}, issued))
    print(f"Authorization saved privately to {config['token_path']}")


def _https(value: object, label: str) -> str:
    if not isinstance(value, str) or urlparse(value).scheme != "https" or not urlparse(value).netloc:
        raise KakaoError(f"{label} must be an absolute https URL")
    return value


def validate_manifest(path: Path) -> tuple[str, list[dict]]:
    manifest = _read_json(path)
    issue_id = manifest.get("issue_id")
    cards = manifest.get("cards")
    if not isinstance(issue_id, str) or not issue_id.strip():
        raise KakaoError("manifest.issue_id must be a non-empty string")
    if not isinstance(cards, list) or not 1 <= len(cards) <= 5:
        raise KakaoError("manifest.cards must contain 1 to 5 cards")
    validated = []
    seen_keys = set()
    for index, card in enumerate(cards, 1):
        if not isinstance(card, dict):
            raise KakaoError(f"cards[{index}] must be an object")
        title = card.get("title")
        description = card.get("description")
        sha = card.get("png_sha256")
        if not isinstance(title, str) or not title.strip():
            raise KakaoError(f"cards[{index}].title must be non-empty")
        if not isinstance(description, str) or not description.strip():
            raise KakaoError(f"cards[{index}].description must be non-empty")
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha):
            raise KakaoError(f"cards[{index}].png_sha256 must be 64 hex characters")
        image = _https(card.get("image_url"), f"cards[{index}].image_url")
        source = _https(card.get("source_url"), f"cards[{index}].source_url")
        download = _https(card.get("download_url"), f"cards[{index}].download_url")
        key_material = json.dumps([issue_id, sha.lower(), image, source, download], separators=(",", ":"))
        card_key = hashlib.sha256(key_material.encode()).hexdigest()
        if card_key in seen_keys:
            raise KakaoError(f"cards[{index}] duplicates another card in this manifest")
        seen_keys.add(card_key)
        validated.append({
            "key": card_key,
            "sha": sha.lower(),
            "template": {
                "object_type": "feed",
                "content": {"title": title, "description": description, "image_url": image,
                            "link": {"web_url": source, "mobile_web_url": source}},
                "buttons": [
                    {"title": "기사 보기", "link": {"web_url": source, "mobile_web_url": source}},
                    {"title": "이미지 다운로드", "link": {"web_url": download, "mobile_web_url": download}},
                ],
            },
            "urls": {"image": image, "source": source, "download": download},
        })
    return issue_id, validated


def _receipts(config: dict) -> dict:
    value = _read_json(config["receipt_path"], required=False)
    if not value:
        value = {"version": 1, "records": {}}
    if not isinstance(value.get("records"), dict):
        raise KakaoError("Receipt file is invalid")
    return value


def _send_unlocked(config: dict, manifest_path: Path) -> None:
    issue_id, cards = validate_manifest(manifest_path)
    receipts = _receipts(config)
    records = receipts["records"]
    uncertain = [card for card in cards if records.get(card["key"], {}).get("status") == "unknown"]
    if uncertain:
        card = uncertain[0]
        raise KakaoError(f"Refusing uncertain send for card {card['key'][:12]} (unknown)")
    pending = [card for card in cards if records.get(card["key"], {}).get("status") != "sent"]
    skipped = len(cards) - len(pending)
    if not pending:
        print(f"all {skipped} card(s) already sent; skipped")
        return
    if skipped:
        print(f"skipped {skipped} already-sent card(s); resuming remaining {len(pending)}")
    token = access_token(config, state_locked=True)
    for card in pending:
        key = card["key"]
        record = {"issue_id": issue_id, "png_sha256": card["sha"], "urls": card["urls"],
                  "status": "unknown", "attempted_at": int(time.time())}
        records[key] = record
        _private_json_write(config["receipt_path"], receipts)
        try:
            response = _post_json(SEND_URL, {"template_object": json.dumps(card["template"], ensure_ascii=False)},
                                  token=token, timeout=config["request_timeout"])
        except KakaoError as exc:
            # A 4xx is a confirmed rejection. Transport and 5xx failures remain unknown.
            if isinstance(exc, KakaoRejectedError):
                record["status"] = "failed"
            record["error"] = str(exc)
            _private_json_write(config["receipt_path"], receipts)
            raise
        if response.get("result_code") != 0:
            record.update(status="failed", error="Kakao returned a non-zero result_code")
            _private_json_write(config["receipt_path"], receipts)
            raise KakaoError("Kakao did not confirm message delivery (non-zero result_code)")
        record.update(status="sent", sent_at=int(time.time()))
        record.pop("error", None)
        _private_json_write(config["receipt_path"], receipts)
        print(f"sent {key[:12]} issue={issue_id}")


def send(config: dict, manifest_path: Path) -> None:
    with _state_lock(config):
        _send_unlocked(config, manifest_path)


def status(config: dict, issue_id: str | None) -> None:
    with _state_lock(config):
        records = _receipts(config)["records"]
        selected = [(key, value) for key, value in records.items() if not issue_id or value.get("issue_id") == issue_id]
    print(json.dumps([{"key": key, **value} for key, value in selected], ensure_ascii=False, indent=2))


def resolve_unknown(config: dict, key: str, outcome: str) -> None:
    with _state_lock(config):
        receipts = _receipts(config)
        matches = [item for item in receipts["records"] if item.startswith(key)]
        if len(matches) != 1:
            raise KakaoError("Card key prefix must match exactly one receipt")
        record = receipts["records"][matches[0]]
        if record.get("status") != "unknown":
            raise KakaoError("Only an unknown receipt can be resolved")
        record["status"] = "sent" if outcome == "sent" else "failed"
        record["resolved_at"] = int(time.time())
        record["resolution"] = "manual KakaoTalk check"
        _private_json_write(config["receipt_path"], receipts)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="KakaoTalk send-to-self for economy cards")
    result.add_argument("--config", type=Path, default=DEFAULT_DIR / "config.json")
    commands = result.add_subparsers(dest="command", required=True)
    auth = commands.add_parser("authorize")
    auth.add_argument("--wait-seconds", type=int, default=300)
    dry = commands.add_parser("dry-run")
    dry.add_argument("manifest", type=Path)
    send_cmd = commands.add_parser("send")
    send_cmd.add_argument("manifest", type=Path)
    show = commands.add_parser("status")
    show.add_argument("--issue-id")
    resolve = commands.add_parser("resolve-unknown")
    resolve.add_argument("key")
    resolve.add_argument("--outcome", choices=("sent", "not-sent"), required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "dry-run":
            issue_id, cards = validate_manifest(args.manifest)
            print(json.dumps({"valid": True, "issue_id": issue_id, "cards": len(cards)}, ensure_ascii=False))
            return 0
        config = load_config(args.config)
        if args.command == "authorize":
            authorize(config, args.wait_seconds)
        elif args.command == "send":
            send(config, args.manifest)
        elif args.command == "status":
            status(config, args.issue_id)
        elif args.command == "resolve-unknown":
            resolve_unknown(config, args.key, args.outcome)
        return 0
    except KakaoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
