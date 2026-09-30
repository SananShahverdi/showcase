# Algorithms and data structures

| Implemented algorithm | Input → output | Important invariant |
|---|---|---|
| Event-time windowing | event + 24h history → risk features | Only events at or before event time influence features |
| Lateness/eviction | watermark + event → live/late state | Late events are scored/stored but do not mutate live state |
| Explainable scoring | features + event → bounded score/contributions | Statistical, rule, and total scores remain in [0, 1] |
| Alert policy | score + 0.5 threshold → optional alert | Below-threshold scores remain in monitoring data |
| Feedback metrics | alerts/decisions/scores → precision/FPR/drift | Precision and FPR use reviewed TP + FP as denominator |

`Event`, `RiskFeatures`, `Score`, `ProcessingResult`, and `Alert` preserve event, feature, model, policy, and decision versions. Local per-event feature computation is O(history), bounded by 24-hour eviction; ID deduplication is O(1). Tests cover boundaries, lateness, future leakage, reasons, duplicates, optimistic decisions, monitoring, and export.
