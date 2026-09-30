# Algorithms and data structures

| Implemented algorithm | Input → output | Important invariant |
|---|---|---|
| Scenario correlation | incident telemetry → hypothesis/confidence | Every plan cites metric, log, trace, and runbook evidence |
| Runbook selection | incident enum → stable runbook path | No unavailable document is presented as retrieved content |
| Command policy | command text → allowed/reason | Dangerous patterns and unknown command families fail closed |
| Approval state machine | plan/action/decision → terminal action | Only `pending` can be decided and only `approved` can execute |
| Report generation | terminal plan + audit facts → Markdown/JSON | Reports list only completed commands as actions taken |

Primary structures are UUID-keyed `Incident`, `RemediationPlan`, `RemediationAction`, `EvidenceReference`, `AuditEvent`, and `PostIncidentReport` records. Repository lookup is constant-time in local mode; listing and audit ordering are O(n log n). Unit and integration tests cover policy bypasses, evidence completeness, safe execution, invalid transitions, audit, and export.
