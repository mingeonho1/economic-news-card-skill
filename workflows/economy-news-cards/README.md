# 경제 뉴스 카드 제작

공식 원문으로 확인한 경제·시장 이슈 중 생활 영향이 분명한 뉴스만 골라 1080×1920 스토리 카드로 만든다. 뉴스 하나당 한 장이며, 적합한 기사 수에 따라 **1~5장**을 만든다.

![2026년 9월 17일 Fed 영향 샘플](examples/2026-09-17-fed-impact/market-impact.png)

이 Fed 카드는 생활 영향 중심 모듈과 렌더러를 승인한 `sample_complete` 기록이다. 주간 전체 완료로 세지 않는다. [2026년 9월 9~13일 3장 예시](examples/2026-09-09_to_13/)는 이전 형식의 역사 기록으로 남아 있다.

## 실제 루틴

1. 수요일 20:00 KST에 직전 수요일~화요일의 후보를 찾는다.
2. 공식 원문에서 발표·사건 날짜, 원문 시간대와 KST 날짜, 숫자·단위·비교 기준을 확인한다.
3. 이전 주간 실행과 샘플을 대조해 같은 사건을 제외하고, 생활 연결성이 분명한 서로 다른 뉴스 1~5개를 고른다.
4. Skill에 포함된 HTML/CSS/JavaScript 렌더러로 PNG를 만들고 한글 줄바꿈, 수치, 날짜, 출처, 안전영역을 직접 확인한다.
5. PNG와 `sources.md`, `data.js`, `provenance.md`, `manifest.json`을 실행 폴더에 보관하고 필요하면 ZIP으로 묶는다.

수요일 20:00은 제작 시작 시각이다. 전달 대상으로 카카오톡 `나에게 보내기`를 선택했지만 인증은 연결하지 않았고 실제 전송도 활성화하지 않았다.

## 모델과 도구의 경계

현재 Fed 샘플의 실제 제작 경로는 HTML/CSS/JavaScript와 Chrome Headless이며 GPT Image는 사용하지 않았다. 이미지 생성은 새로운 삽화가 정보 전달에 필요한 경우에만 선택적으로 사용한다. 모델 별칭은 작업 라우팅 설정이고, `provenance.md`에는 실행 환경이 노출한 실제 식별자만 쓴다.

## 폴더

- [실행 Skill](../../skills/weekly-economy-cards/SKILL.md)
- [시장 선정 기준](../../skills/weekly-economy-cards/references/market-selection.md)
- [주간 자동화 훅](automation/weekly-hook.md)
- [전달 계약](automation/delivery.md)
- [디자인 결정](design-decisions.md)
- [검증·패키징 흐름](workflow.md)
- [모델·도구 기록](model-and-tooling.md)
- [현재 Fed 샘플](examples/2026-09-17-fed-impact/)
- [기존 3장 샘플](examples/2026-09-09_to_13/)
- [렌더러 안내](template/)
