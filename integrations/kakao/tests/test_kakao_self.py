import importlib.util
import io
import json
import multiprocessing
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


MODULE_PATH = Path(__file__).parents[1] / "kakao_self.py"
SPEC = importlib.util.spec_from_file_location("kakao_self", MODULE_PATH)
kakao = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kakao)


SHA = "a" * 64


def manifest(cards=1):
    return {
        "issue_id": "2026-W38",
        "cards": [
            {
                "title": f"Card {index}",
                "description": "Summary",
                "image_url": f"https://media.example/card-{index}.png",
                "source_url": f"https://news.example/story-{index}",
                "download_url": f"https://media.example/card-{index}.png?download=1",
                "png_sha256": SHA[:-1] + str(index % 10),
            }
            for index in range(cards)
        ],
    }


def concurrent_send_worker(config, manifest_path, start, post_log):
    def fake_post(*_args, **_kwargs):
        with post_log.open("a", encoding="utf-8") as stream:
            stream.write("POST\n")
        time.sleep(0.1)
        return {"result_code": 0}

    kakao._post_json = fake_post
    start.wait(2)
    with redirect_stdout(io.StringIO()):
        kakao.send(config, manifest_path)


class KakaoSelfTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest_path = self.root / "manifest.json"
        self.config = {
            "client_id": "public-rest-key",
            "client_secret": "private-secret",
            "redirect_uri": "http://127.0.0.1:8765/callback",
            "token_path": self.root / "token.json",
            "receipt_path": self.root / "receipt.json",
            "request_timeout": 1,
        }

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(self, cards=1):
        self.manifest_path.write_text(json.dumps(manifest(cards)), encoding="utf-8")

    def write_token(self):
        kakao._private_json_write(
            self.config["token_path"],
            {"access_token": "access-secret", "refresh_token": "refresh-secret", "expires_at": 9999999999},
        )

    def test_dry_run_makes_no_http_request(self):
        self.write_manifest(5)
        with patch.object(kakao, "urlopen") as mocked, redirect_stdout(io.StringIO()) as output:
            result = kakao.main(["dry-run", str(self.manifest_path)])
        self.assertEqual(result, 0)
        self.assertIn('"cards": 5', output.getvalue())
        mocked.assert_not_called()

    def test_rejects_more_than_five_cards(self):
        self.write_manifest(6)
        with self.assertRaisesRegex(kakao.KakaoError, "1 to 5"):
            kakao.validate_manifest(self.manifest_path)

    def test_rejects_duplicate_cards_in_one_manifest(self):
        value = manifest(1)
        value["cards"].append(dict(value["cards"][0]))
        self.manifest_path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(kakao.KakaoError, "duplicates"):
            kakao.validate_manifest(self.manifest_path)

    def test_refresh_merges_optional_refresh_token(self):
        old = {"access_token": "old-access", "refresh_token": "keep-refresh", "expires_at": 0}
        with patch.object(kakao, "_post_json", return_value={"access_token": "new-access", "expires_in": 3600}) as post:
            renewed = kakao.refresh(self.config, old)
        self.assertEqual(renewed["access_token"], "new-access")
        self.assertEqual(renewed["refresh_token"], "keep-refresh")
        fields = post.call_args.args[1]
        self.assertEqual(fields["grant_type"], "refresh_token")
        self.assertEqual(fields["client_secret"], "private-secret")
        self.assertEqual(self.config["token_path"].stat().st_mode & 0o777, 0o600)

    def test_send_success_and_already_sent_skip(self):
        self.write_manifest()
        self.write_token()
        with patch.object(kakao, "_post_json", return_value={"result_code": 0}) as post, redirect_stdout(io.StringIO()) as output:
            kakao.send(self.config, self.manifest_path)
            kakao.send(self.config, self.manifest_path)
        self.assertEqual(post.call_count, 1)
        self.assertIn("already sent; skipped", output.getvalue())
        self.assertEqual(post.call_args.args[0], kakao.SEND_URL)
        payload = json.loads(post.call_args.args[1]["template_object"])
        self.assertEqual(payload["object_type"], "feed")
        self.assertEqual(len(payload["buttons"]), 2)
        receipt = json.loads(self.config["receipt_path"].read_text(encoding="utf-8"))
        self.assertEqual(next(iter(receipt["records"].values()))["status"], "sent")

    def test_uncertain_send_stops_and_requires_resolution(self):
        self.write_manifest(2)
        self.write_token()
        uncertain = kakao.KakaoError("Kakao API response was not confirmed (network error or timeout)")
        with patch.object(kakao, "_post_json", side_effect=uncertain) as post:
            with self.assertRaisesRegex(kakao.KakaoError, "not confirmed"):
                kakao.send(self.config, self.manifest_path)
        self.assertEqual(post.call_count, 1)
        receipt = json.loads(self.config["receipt_path"].read_text(encoding="utf-8"))
        key, record = next(iter(receipt["records"].items()))
        self.assertEqual(record["status"], "unknown")
        kakao.resolve_unknown(self.config, key[:12], "not-sent")
        updated = json.loads(self.config["receipt_path"].read_text(encoding="utf-8"))
        self.assertEqual(updated["records"][key]["status"], "failed")

    def test_http_rejection_is_failed_without_raw_body(self):
        request_error = HTTPError(kakao.SEND_URL, 403, "Forbidden secret-body", {}, io.BytesIO(b"token=leak"))
        with patch.object(kakao, "urlopen", side_effect=request_error):
            with self.assertRaises(kakao.KakaoError) as raised:
                kakao._post_json(kakao.SEND_URL, {}, token="access-secret", timeout=1)
        self.assertIsInstance(raised.exception, kakao.KakaoRejectedError)
        text = str(raised.exception)
        self.assertIn("HTTP 403", text)
        self.assertNotIn("secret-body", text)
        self.assertNotIn("token=leak", text)
        self.assertNotIn("access-secret", text)

    def test_http_5xx_send_remains_unknown(self):
        self.write_manifest()
        self.write_token()
        server_error = HTTPError(kakao.SEND_URL, 502, "upstream secret", {}, io.BytesIO(b"token=leak"))
        with patch.object(kakao, "urlopen", side_effect=server_error):
            with self.assertRaisesRegex(kakao.KakaoUncertainError, "HTTP 502"):
                kakao.send(self.config, self.manifest_path)
        receipt = json.loads(self.config["receipt_path"].read_text(encoding="utf-8"))
        self.assertEqual(next(iter(receipt["records"].values()))["status"], "unknown")

    def test_resumes_only_unsent_card_after_manual_resolution(self):
        self.write_manifest(2)
        self.write_token()
        uncertain = kakao.KakaoUncertainError("Kakao API response was not confirmed (network error or timeout)")
        with patch.object(kakao, "_post_json", side_effect=[{"result_code": 0}, uncertain]), redirect_stdout(io.StringIO()):
            with self.assertRaises(kakao.KakaoUncertainError):
                kakao.send(self.config, self.manifest_path)
        receipt = json.loads(self.config["receipt_path"].read_text(encoding="utf-8"))
        unknown_key = next(key for key, record in receipt["records"].items() if record["status"] == "unknown")
        kakao.resolve_unknown(self.config, unknown_key[:12], "not-sent")

        with patch.object(kakao, "_post_json", return_value={"result_code": 0}) as post, redirect_stdout(io.StringIO()) as output:
            kakao.send(self.config, self.manifest_path)
        self.assertEqual(post.call_count, 1)
        self.assertIn("skipped 1 already-sent", output.getvalue())
        updated = json.loads(self.config["receipt_path"].read_text(encoding="utf-8"))
        self.assertEqual([record["status"] for record in updated["records"].values()].count("sent"), 2)

    def test_process_lock_prevents_concurrent_duplicate_send(self):
        self.write_manifest()
        self.write_token()
        post_log = self.root / "posts.log"
        context = multiprocessing.get_context("fork")
        start = context.Event()
        processes = [
            context.Process(
                target=concurrent_send_worker,
                args=(self.config, self.manifest_path, start, post_log),
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        start.set()
        for process in processes:
            process.join(3)
        self.assertEqual([process.exitcode for process in processes], [0, 0])
        self.assertEqual(post_log.read_text(encoding="utf-8").splitlines(), ["POST"])

    def test_oauth_callback_requires_matching_state(self):
        status, result, body = kakao._parse_oauth_callback(
            "/callback?code=never-print&state=wrong", "expected-state"
        )
        self.assertEqual(status, 400)
        self.assertEqual(result, {})
        self.assertIn(b"state", body)

        status, result, _ = kakao._parse_oauth_callback(
            "/callback?code=authorization-secret&state=expected-state", "expected-state"
        )
        self.assertEqual(status, 200)
        self.assertEqual(result, {"code": "authorization-secret"})


if __name__ == "__main__":
    unittest.main()
