# Source verification contract

For each card, record the institution, original URL, source publication timestamp and timezone, KST date, event/effective date, indicator period, value, unit, comparison baseline, seasonal-adjustment status, and provisional/final status when available.

Before rendering, compare these fields against `data.js`, `sources.md`, and the duplicate ledger formed from earlier manifests, sources, and samples.

| Check | Example failure |
| --- | --- |
| Original source | News summary cited although the institution's release exists |
| Publication and event date | Release date presented as the policy effective date |
| Timezone | A U.S. close and an earlier Korean session treated as the same post-announcement reaction |
| Period | August observation presented as September data |
| Number and unit | Percent confused with percentage points |
| Comparison | Month-over-month caption used for a year-over-year value |
| Adjustment | Seasonally adjusted and unadjusted series mixed |
| Scope | Total employment presented as youth employment |
| Duplicate | The same decision repeated with a new article URL but no new development |

When an original page changes or links to a supporting table, note which page and table produced each number. Keep values from one compatible source series; do not combine a level from one provider with a change rate from another.

The `그래서 우리한텐?` block is interpretation. Use conditional language such as `부담이 될 수 있어요`, name the affected group and pathway, and state an important dependency when useful. Never upgrade a plausible pathway into a guaranteed outcome or infer a single cause from timing alone.
