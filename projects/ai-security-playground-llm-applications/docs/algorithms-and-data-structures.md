# Algorithms and data structures

| Algorithm | Where | Notes |
|---|---|---|
| Unicode canonicalization | `apps.canonicalize` | NFKC normalization and whitespace collapsing before matching, so full-width or spaced variants are caught. |
| Instruction-override detection | `apps.contains_injection` | Case-insensitive regular expressions over canonical text. |
| Active-markup detection | `apps.contains_active_markup` | Script-capable tags, inline event handlers, `javascript:` URLs. |
| Output encoding | `HardenedApp` | `html.escape` with quotes before returning text. |
| Virtual path allowlist | `SyntheticToolSandbox.safe_file_lookup` | Rejects absolute and traversal paths and unknown documents. |
| Read-only SQL | `SyntheticToolSandbox.safe_sql` | A single `SELECT`; mutating keywords go to the approval path. |
| Role/tool authorization | `HardenedApp` + scenario matrix | Tools allowed per role; external writes still require approval. |
| Assessment reconciliation | `SecurityService.run_assessment` | Exposures = successful vulnerable runs; mitigations = hardened runs that triggered a control and blocked the attack; rate = mitigations / hardened runs. |

## Data structures

| Structure | Purpose |
|---|---|
| `Scenario` | Versioned attack case with payload, threat, expected outcomes, and `allowed_tools_by_role`. |
| `ExecutionResult` | One run: mode, role, verdict, requested vs executed tools, control IDs, ordered `SecurityDecision`s, synthetic effect, approval ID, duration. |
| `Approval` | One-time approval with `pending → approved/denied → consumed` states; consuming twice is refused. |
| `SecurityReport` | Stored assessment with counts, rate, and all 12 results. |

All lookups are dictionary-based; each run is linear in the payload length.
