# Run package

Create a dated directory using the weekly end date. `N` is the selected card count from 1 to 5.

```text
runs/YYYY-MM-DD/
├── weekly-economy-01.png
├── ...
├── weekly-economy-0N.png
├── data.js
├── sources.md
├── provenance.md
├── manifest.json
└── economy-stories.zip        # optional transport bundle
```

`manifest.json` records the edition type, coverage period, item identity, card count, output files, status, and whether the edition counts toward weekly coverage. Mark a weekly edition complete only after the full period is selected, rendered, and packaged. Use `sample_complete` for an approved sample; it enters duplicate checks but does not advance the completed-week boundary.

`provenance.md` records the creation date, coverage period, palette, rendering command, verification/review roles, and actual model or tool identifiers only when the runtime exposes them. Configured profile aliases are not actual execution evidence. Do not invent model IDs.

The completion notice should state the actual card count and provide the available previews and bundle path. External delivery requires a separately configured client and authentication; the public Skill contains neither.
