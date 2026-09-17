# 카드 렌더러 안내

현재 기준 렌더러는 Skill이 자체 포함한 [`skills/weekly-economy-cards/assets/renderer/`](../../../skills/weekly-economy-cards/assets/renderer/) 한 곳에서 관리한다. 이 `template/` 폴더는 중복 코드를 두지 않고 기준 위치만 안내한다.

새 실행 폴더에 렌더러를 복사하고 `data.js`의 `cards`를 1~5개 작성한다.

```bash
cp -R ../../../skills/weekly-economy-cards/assets/renderer ./economy-card-render
cd economy-card-render
chmod +x render.sh
./render.sh
```

결과는 `output/weekly-economy-01.png`부터 실제 `cards` 수만큼 생성된다. 모든 PNG의 문장, 수치, 출처, 안전영역과 1080×1920 크기를 확인한 뒤 실행 패키지로 옮긴다.
