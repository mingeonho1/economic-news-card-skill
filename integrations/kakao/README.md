# KakaoTalk 나에게 보내기 (설정 대기 중)

이 연동은 경제 카드 1~5장을 로그인한 사용자의 카카오톡 나와의 채팅방에 각각 피드 메시지로 보냅니다. 친구에게 보내는 API는 구현하지 않았습니다. Kakao Developers 앱 설정, 비공개 설정 파일, OAuth 동의, 공개 HTTPS 이미지 및 다운로드 호스팅, 토큰 준비가 끝나기 전까지는 **실제로 연결된 상태가 아닙니다**.

Python 3 표준 라이브러리만 사용합니다. 연동에 사용하는 공식 API는 [인가 코드 및 토큰 API](https://developers.kakao.com/docs/ko/kakaologin/rest-api)와 [`/v2/api/talk/memo/default/send`](https://developers.kakao.com/docs/ko/kakaotalk-message/rest-api#나에게-기본-템플릿으로-메시지-발송)입니다.

## Kakao Developers 설정

사용할 Kakao Developers 앱에서 다음 항목을 설정합니다.

1. 카카오 로그인을 활성화합니다.
2. Redirect URI에 `http://127.0.0.1:8765/callback`을 등록합니다. CLI는 의도적으로 `127.0.0.1`에만 바인딩합니다. Kakao Developers 콘솔에서 이 루프백 URI를 허용하지 않으면 콘솔이 허용하는 정확한 루프백 형식을 등록하고 설정 파일에도 같은 URI를 입력해야 합니다. CLI가 허용하는 형식은 `http://127.0.0.1:<port>/callback`뿐입니다.
3. 카카오톡 메시지 동의 항목(`talk_message`)을 활성화합니다.
4. 제품 링크 관리의 웹 도메인에 버튼 링크로 사용하는 `source_url`과 `download_url`의 도메인을 등록합니다. 공식 문서의 웹 도메인 등록 요건은 메시지의 웹 링크 대상에 적용됩니다. `image_url`은 실제 이미지 파일을 반환하는 공개 HTTPS URL이어야 하지만, 이 문서에서는 공식 근거 없이 이미지 호스트까지 웹 도메인에 등록해야 한다고 가정하지 않습니다.
5. REST API 키를 `client_id`로 사용합니다. 해당 REST API 키에 Client Secret이 활성화되어 있다면 Client Secret도 설정합니다. 새로 발급된 REST API 키는 현재 Client Secret이 기본 활성화됩니다.

GitHub를 호스팅에 사용할 경우 `image_url`에는 이미지 파일 자체를 반환하는 `https://raw.githubusercontent.com/...` 주소를 사용합니다. `source_url`이나 `download_url`에 `https://github.com/...` 주소를 사용한다면 제품 링크 관리에 `github.com`을 등록합니다. 저장소 페이지 주소는 이미지 파일 URL이 아니므로 `image_url`로 사용할 수 없습니다.

키, Client Secret, 토큰, 인가 코드, 전송 기록은 커밋하지 않습니다. 기본 저장 위치는 이 저장소 밖의 `~/.config/economic-news-card/kakao/`이며, 상태 파일은 `0600` 권한으로 원자적으로 저장합니다.

`~/.config/economic-news-card/kakao/config.json` 예시:

```json
{
  "client_id": "YOUR_REST_API_KEY",
  "client_secret": "YOUR_CLIENT_SECRET_IF_ENABLED",
  "redirect_uri": "http://127.0.0.1:8765/callback",
  "request_timeout": 15
}
```

`chmod 600 ~/.config/economic-news-card/kakao/config.json`을 실행합니다. 키를 파일에 저장하지 않으려면 `KAKAO_REST_API_KEY`와 선택 항목인 `KAKAO_CLIENT_SECRET` 환경 변수를 사용합니다. 필요하면 `token_path`, `receipt_path`, `lock_path` 설정으로 비공개 저장 위치를 바꿀 수 있지만, CLI는 이 Git 저장소 안에 해당 파일을 쓰지 않습니다.

## 최초 1회 인증

```bash
python3 integrations/kakao/kakao_self.py authorize
```

명령을 실행하면 REST API 키와 임의의 `state`만 포함한 OAuth URL을 출력한 뒤 로컬 콜백을 최대 5분 동안 기다립니다. 출력된 URL을 브라우저에서 열고 로그인한 다음 동의합니다. 인가 코드는 메모리에서 바로 토큰으로 교환하며 출력하지 않습니다. 액세스 토큰은 자동으로 갱신합니다. 카카오는 기존 리프레시 토큰의 만료가 임박한 경우에만 새 리프레시 토큰을 반환하므로, 토큰 파일을 갱신할 때 응답에 포함된 선택 필드만 병합합니다.

## 매니페스트 검증 및 전송

전송기는 공개 URL을 매니페스트로 전달받습니다. 파일을 공개하거나 Git에 푸시하는 기능은 없습니다.

```json
{
  "issue_id": "2026-W38",
  "cards": [
    {
      "title": "이번 주 경제 뉴스",
      "description": "핵심 요약",
      "image_url": "https://media.example.com/2026-W38/card-1.png",
      "source_url": "https://news.example.com/article",
      "download_url": "https://media.example.com/2026-W38/card-1.png?download=1",
      "png_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    }
  ]
}
```

설정 파일이나 토큰을 읽지 않고, 네트워크 요청도 보내지 않는 검증 명령:

```bash
python3 integrations/kakao/kakao_self.py dry-run /absolute/path/to/kakao-manifest.json
```

저장소에 포함된 Fed 영향 샘플 매니페스트는 다음 명령으로 검증합니다.

```bash
python3 integrations/kakao/kakao_self.py dry-run integrations/kakao/examples/fed-impact.json
```

이 샘플의 공개 URL은 현재 브랜치 내용이 GitHub의 `main` 브랜치에 올라간 뒤에만 실제로 열립니다. 푸시 전에는 실전 전송에 사용하지 않고 `dry-run` 검증에만 사용합니다.

실제 전송은 다음 명령을 명시적으로 실행할 때만 이뤄집니다.

```bash
python3 integrations/kakao/kakao_self.py send /absolute/path/to/kakao-manifest.json
```

카드마다 `기사 보기`와 `이미지 다운로드` 버튼이 있는 별도 카카오 피드 메시지를 보냅니다. 비공개 전송 기록 키는 `issue_id`, PNG SHA-256, 이미지·출처·다운로드 URL을 모두 반영합니다. 전송 성공이 확인된 카드는 다음 실행에서 건너뛰므로, 일부 카드만 전송된 묶음도 확인 후 나머지 카드부터 이어서 보낼 수 있습니다. 모든 카드가 이미 전송됐다면 네트워크 요청 없이 성공으로 종료하고 건너뛴 결과를 출력합니다.

HTTP 4xx처럼 카카오가 요청 거부를 명확히 응답한 경우는 `failed`로 기록합니다. 타임아웃, 전송 중 네트워크 오류, HTTP 5xx 서버 오류는 카카오가 요청을 처리했는지 확정할 수 없으므로 `unknown`으로 기록하고 묶음 전송을 중단합니다. 이미 전송됐을 가능성이 있으므로 확인 전에는 재전송을 차단합니다.

전송·토큰 갱신·전송 기록 확인 및 수정은 같은 로컬 잠금 파일로 직렬화합니다. 따라서 같은 설정으로 여러 프로세스가 동시에 실행돼도 동일 카드를 중복 전송하지 않습니다. 이 잠금은 Python 표준 라이브러리의 `fcntl.flock`을 사용하는 macOS 및 Linux용입니다.

카카오톡 나와의 채팅방에서 실제 수신 여부를 확인한 뒤에만 불확실한 전송 상태를 수동으로 해소합니다.

```bash
python3 integrations/kakao/kakao_self.py status --issue-id 2026-W38
python3 integrations/kakao/kakao_self.py resolve-unknown KEY_PREFIX --outcome sent
python3 integrations/kakao/kakao_self.py resolve-unknown KEY_PREFIX --outcome not-sent
```

`not-sent`로 처리한 뒤에는 명시적인 `send` 명령으로 해당 카드를 다시 보낼 수 있습니다. 카카오톡을 확인하지 않은 상태에서 `not-sent`를 사용하면 안 됩니다.

## 테스트

```bash
python3 -m unittest discover -s integrations/kakao/tests -v
```
