---
name: weekly-economy-cards
description: Create one to five verified Korean economy and market news cards for Instagram Stories, selecting only official-source stories with clear practical impact and rendering reproducible 1080×1920 PNGs.
metadata:
  short-description: Verified life-impact economy story cards
---

# Weekly Economy Cards

Create **one to five** Korean Instagram Story cards for the weekly period. Select only new, source-verifiable economy or market stories with a clear path to household spending, loans, savings, investments, or jobs. Do not fill a fixed card count.

## Working method

1. At Wednesday 20:00 KST, read the completed-week ledger. When it exists, select the earliest unfinished Wednesday-through-Tuesday period: the previous completed weekly end date plus one day through plus seven days. Process missed weeks one at a time; never merge or skip them, and never build a future or incomplete week. Only when no completed-week ledger exists, select and record the most recently finished Wednesday-through-Tuesday period before run time. A normal 2026-09-23 run covers 2026-09-16 through 22.
2. Check prior `manifest.json`, `sources.md`, weekly runs, and samples before research. `sample_complete` and partial items remain in duplicate checks but do not advance the weekly continuity boundary.
3. Collect candidates from official institutions, exchanges, filings, and company releases. Apply [market-selection.md](references/market-selection.md), then keep one to five distinct stories whose life-impact score is at least 1 and total score is at least 5.
4. Verify each selected story against its original source. Read [source-verification.md](references/source-verification.md) before writing card data. Check publication and event dates, source timezone and KST date, numbers, units, comparisons, status, and duplicate identity.
5. Put confirmed facts in the headline and explanation. Use conditional language in `그래서 우리한텐?`; do not turn sequence into causation or give investment advice.
6. Copy `assets/renderer/` into the run workspace, edit its `data.js`, and render one card per `cards` entry. The Skill is self-contained and must not depend on `workflows/` files.
7. Open every PNG. Check reading order, Korean line breaks, exact facts, safe areas, source date, and 1080×1920 dimensions. Shorten the copy or simplify the visual when it fails.
8. Package the PNGs, source notes, input data, provenance, manifest, and optional ZIP according to [run-package.md](references/run-package.md).

## Configured profiles and actual execution

When these profiles are available, Claude uses `Fable5.1 high`, `Opus5.0 medium`, and `Sonnet5 medium`; Codex uses `Astra high`, `Sol medium`, and `Terra medium`; independent review uses `Astra xhigh`.

| Responsibility | Runtime | Configured alias |
| --- | --- | --- |
| Editorial planning and source conflicts | Claude | Fable5.1 high |
| General implementation | Claude | Opus5.0 medium |
| Mechanical reads and commands | Claude | Sonnet5 medium |
| Planning and decisions | Codex | Astra high |
| Implementation | Codex | Sol medium |
| Commands and tests | Codex | Terra medium |
| Independent review | Codex | Astra xhigh |

These aliases describe routing configuration, not proof of a particular run. Record actual execution only from model or tool identifiers exposed by the runtime. Never infer an actual model from an alias.

Parallel work is safe for independent source checks and visual review. Give each worker a bounded output and source list; do not let multiple workers edit the same data or design file.

## Non-negotiable constraints

- One to five cards per weekly edition; one news item per card; no filler story.
- 1080×1920 PNG; title at most two lines; practical impact in short, readable blocks.
- Keep the v3 paper system and cycle one weekly palette: `green-coral → teal-orange → olive-terracotta`.
- Show an abbreviated original source and release date on the card. Keep full URLs, timezone decisions, and verification notes in `sources.md`.
- Use the bundled HTML/CSS/JavaScript renderer for exact copy and layout. GPT Image is optional only when a genuinely new illustration is needed.
- Preserve the 2026-09-17 Fed card as `sample_complete`, not a completed weekly run. Preserve the older three-card example as history.

## Read when needed

- Candidate selection and duplicate handling: [market-selection.md](references/market-selection.md)
- Primary-source and wording checks: [source-verification.md](references/source-verification.md)
- Visual hierarchy and palette: [design-system.md](references/design-system.md)
- Output status and artifacts: [run-package.md](references/run-package.md)
