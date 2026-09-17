# Weekly Economy News Card Skill

**왜 만들었나:** 검증된 경제·주식·금융 뉴스를 매주 읽기 쉬운 인스타그램 스토리 카드로, 세션 기억 없이도 같은 기준으로 다시 만들기 위해서다.

카드 비주얼은 기본 내장 GPT Image 워크플로를 쓰고, 숫자·날짜·출처는 이미지 생성과 분리해 원문으로 검증한다. 한 주에 3장, 카드마다 핵심 수치 하나와 `그래서 우리한텐?` 한두 줄을 담는다.

## 들어 있는 것

- [실행 Skill](skills/weekly-economy-cards/SKILL.md): 뉴스 선택, 주차 계산, 색상 순환, 카드 문장, 파일 패키징 규칙
- [주간 훅](workflows/economy-news-cards/automation/weekly-hook.md): 직전 종료일 다음 날부터 수집하고, 일요일 20:00 KST에 실행하는 반복 계약
- [원문 검증](skills/weekly-economy-cards/references/source-verification.md): 수치·기간·단위·비교 기준을 발표기관 원문과 대조하는 체크리스트
- [디자인·모델 기록](workflows/economy-news-cards/): 레퍼런스에서 추출한 정보 위계, GPT Image 사용 경계, 템플릿 보조 경로
- [다운로드 예시](workflows/economy-news-cards/examples/2026-09-09_to_13/economy-stories.zip): PNG 3장, `sources.md`, 입력 데이터, 생성 기록을 묶은 실제 패키지

## 설치

```bash
git clone https://github.com/mingeonho1/economic-news-card-skill.git
cp -R economic-news-card-skill/skills/weekly-economy-cards ~/.codex/skills/
```

설치 뒤 경제 뉴스 카드 제작을 요청하면 `weekly-economy-cards` Skill을 불러온다. 카드의 최종 비주얼은 기본 내장 GPT Image로 만들고, 한 글자도 틀리면 안 되는 수치·날짜·차트는 [템플릿 렌더러](workflows/economy-news-cards/template/)로 보조한다.

## 한 주 실행 결과

`runs/YYYY-MM-DD/`에 다음을 함께 남긴다.

```text
weekly-economy-01.png
weekly-economy-02.png
weekly-economy-03.png
sources.md
data.js
provenance.md
economy-stories.zip
```

공식 OpenAI 이미지 생성 문서와 모델 선택 근거는 [모델·도구 기록](workflows/economy-news-cards/model-and-tooling.md)에, 재현 규칙은 [전체 워크플로](workflows/economy-news-cards/workflow.md)에 적어 두었다.
