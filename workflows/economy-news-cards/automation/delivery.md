# 매주 이미지 받기

카드 생성과 외부 메시지 전송은 별도 단계다. 이 저장소를 설치했다고 Slack·카카오톡 권한이나 외부 전송이 자동으로 연결되지는 않는다. 받는 사람과 채널을 지정하고 인증을 연결한 뒤에 전송 단계를 활성화한다.

## Slack — PNG 원본을 받을 때

워크스페이스에 봇을 설치하고 `files:write` 권한과 대상 대화 ID를 준비한다. 채널에서는 봇을 초대한다. 사용자 ID로 DM을 새로 열려면 `im:write`도 필요하다. 이미 확인된 DM 대화 ID를 사용하면 DM 생성 호출은 생략할 수 있다.

전송 순서는 다음과 같다.

1. 검증된 각 PNG의 파일명과 바이트 길이로 `files.getUploadURLExternal`을 호출한다.
2. 반환된 업로드 URL로 실제 PNG 바이트를 보낸다.
3. 모은 파일 ID들을 `files.completeUploadExternal`에 대상 `channel_id`와 함께 전달한다. 이 단계까지 성공해야 상대 대화방에 공유된 것이다.

외부 공개 이미지 서버 없이 원본 파일을 첨부할 수 있다. 성공 응답의 파일 ID, 대상, 주차, PNG 해시를 실행 폴더의 `delivery.json`에 남겨 같은 결과를 중복 발송하지 않는다. 시간 초과로 성공 여부가 모호하면 무조건 다시 보내지 말고 전송 상태부터 확인한다.

공식 근거: [업로드 URL 발급](https://docs.slack.dev/reference/methods/files.getUploadURLExternal/), [업로드 완료와 공유](https://docs.slack.dev/reference/methods/files.completeUploadExternal/), [DM 열기](https://docs.slack.dev/reference/methods/conversations.open/).

## 카카오톡 — 나와의 채팅에 받기

개발자 앱, 카카오 로그인, 등록된 리다이렉트 URI, `talk_message` 동의, 사용자 OAuth 토큰을 연결해야 한다. 나에게 보내기 API는 로그인한 사용자의 나와의 채팅으로 보낸다.

이미지는 외부에서 접근 가능한 URL을 넣는 메시지 템플릿 방식이다. 로컬 PNG를 Slack처럼 원본 파일로 바로 첨부하는 것과 다르므로, 원본 다운로드가 필요하면 접근 가능한 다운로드 링크를 별도로 준비한다. 사용자의 로컬 파일 경로를 링크로 보내면 다른 기기에서 받을 수 없다.

이 방식은 임의의 일반 단톡방 자동 발송 기능이 아니다. 친구 발송은 별도 권한·서비스 가입·동의 조건이 있고, 채널 비즈메시지는 별도 상품이다.

공식 근거: [카카오톡 메시지 REST API](https://developers.kakao.com/docs/ko/kakaotalk-message/rest-api), [이미지·링크 조건](https://developers.kakao.com/docs/ko/message-template/faq), [수신 대상 구분](https://developers.kakao.com/docs/ko/kakaotalk-message/faq).

## 오후 8시의 의미

현재 주간 루틴은 **수요일 오후 8시 한국시간에 제작을 시작**한다. 외부 메시지 전달 시각은 아직 설정되어 있지 않다.

정확히 오후 8시 수신을 원하면, 연결 후 실행 시간을 앞당겨 제작·검증을 먼저 끝내고 오후 8시에 공유하는 방식으로 바꾼다. 8시에 생성을 시작하면서 같은 시각에 완성본을 보낸다고 약속하지 않는다. 정시 전까지 검증이 끝나지 않으면 미완성 카드를 보내지 않고 실패 또는 지연을 알린다. 로컬 실행 방식을 선택하면 실행 기기가 그 시간에 동작할 수 있어야 한다.

예를 들어 같은 주간 자동화를 수요일 19:00과 20:00에 실행하고, 19:00에는 제작·검증·허가된 이미지 호스팅을 끝낸 뒤 종료한다. 20:00에는 해당 주차의 완료 상태와 이미지 링크를 확인해 전송만 수행한다. 한 시간 동안 프로세스를 대기시키거나 제작 시간을 정시 도착으로 간주하지 않는다. 20:00 결과 알림에는 이미지와 개별 원본 링크를 포함한다. 이 일정은 계정 연결과 시험 전송을 마친 뒤 활성화한다.

Slack의 `chat.scheduleMessage`는 메시지 예약 기능이다. `attachments`는 PNG 바이트를 첨부하는 필드가 아니다. 사전 업로드한 이미지를 참조하려면 파일 접근권한까지 별도로 확인해야 한다. 따라서 파일 업로드·공유와 메시지 예약을 같은 API로 오해하지 않는다. [예약 API](https://docs.slack.dev/reference/methods/chat.scheduleMessage/), [Slack 파일 이미지 참조](https://docs.slack.dev/reference/block-kit/composition-objects/slack-file-object/).

## 연결 전에 준비할 것

받을 서비스, 사용자/대화/채널 ID, 필요한 앱 권한을 확인한다. 토큰은 Git 저장소나 채팅에 적지 않고 로컬 환경변수·키체인 등 실행 환경의 비밀 저장소에 둔다. 전송 성공을 확인한 뒤에만 `delivery.json`을 성공으로 기록한다.

저장소에는 [카카오톡 나에게 보내기 클라이언트](../../../integrations/kakao/README.md)가 포함되어 있다. 먼저 `dry-run`으로 메시지를 확인하고 계정 연결 후 `send`를 실행한다. 인증정보와 활성화된 일정은 포함하지 않는다. Slack은 위 API 연결 절차만 문서화했으며 클라이언트는 제공하지 않는다. 검증일: 2026-09-17.
