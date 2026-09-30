"""Synthetic order-to-fulfilment event log used by the demo seed.

The case IDs, activities, timestamps, and resources are invented. The console's
event-log editor starts with the same CSV so the seeded report can be re-run.
"""

from process_mining_workflow_automation_analyzer.domain.models import AnalysisConfig

DEMO_CSV = """case_id,activity,timestamp,resource
ORD-1042,Order received,2026-06-01T08:00:00Z,portal
ORD-1042,Credit review,2026-06-01T08:06:00Z,credit-team
ORD-1042,Manual correction,2026-06-03T12:30:00Z,ops
ORD-1042,Credit review,2026-06-03T13:00:00Z,credit-team
ORD-1042,Fulfilled,2026-06-03T14:00:00Z,warehouse
ORD-1043,Order received,2026-06-01T09:00:00Z,portal
ORD-1043,Credit review,2026-06-01T09:10:00Z,credit-team
ORD-1043,Fulfilled,2026-06-01T10:00:00Z,warehouse
ORD-1044,Order received,2026-06-01T10:00:00Z,portal
ORD-1044,Fulfilled,2026-06-01T10:20:00Z,warehouse"""

DEMO_CONFIG = AnalysisConfig(sla_seconds=86_400, bottleneck_seconds=86_400, bottleneck_min_frequency=1)
