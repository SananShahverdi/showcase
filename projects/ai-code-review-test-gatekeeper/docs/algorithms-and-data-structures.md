# Algorithms and data structures

| Implemented algorithm | Input → output | Important invariant |
|---|---|---|
| Unified-diff mapper | diff hunks → changed path/new-line/content | Removed lines never trigger added-code rules |
| Finding normalization | changed line + rule → finding/fingerprint | Fingerprints are stable for rule/path/line/content |
| Grounded review writer | findings + changed lines → summary/comments | Every inline comment resolves to a changed line |
| Policy gate | test/coverage/findings → status/reasons | Tests or critical findings block; warnings/low coverage request changes |
| Trend aggregation | filtered report history → counts/rules | Pass rate uses all matching completed reviews |

`ChangedLine`, `Finding`, `AnalysisResult`, and `ReviewReport` preserve evidence through the pipeline. Parsing and rule evaluation are O(lines + findings); recurring-rule aggregation is O(reports × findings). Tests include multiple hunks, removed lines, coordinates, deduplication, gate states, idempotency, filters, and trends.
