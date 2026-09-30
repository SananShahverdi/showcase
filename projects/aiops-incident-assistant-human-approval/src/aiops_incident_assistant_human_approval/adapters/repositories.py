from typing import List, Dict, Optional
from uuid import UUID
from aiops_incident_assistant_human_approval.domain.models import AuditEvent, Incident, RemediationPlan, PostIncidentReport

class InMemoryRepository:
    def __init__(self):
        self.incidents: Dict[UUID, Incident] = {}
        self.plans: Dict[UUID, RemediationPlan] = {}
        self.reports: Dict[UUID, PostIncidentReport] = {}
        self.audit_events: Dict[UUID, AuditEvent] = {}

    def save_incident(self, incident: Incident):
        self.incidents[incident.id] = incident

    def get_incident(self, incident_id: UUID) -> Optional[Incident]:
        return self.incidents.get(incident_id)

    def get_incidents(self) -> List[Incident]:
        return sorted(self.incidents.values(), key=lambda item: item.created_at, reverse=True)

    def save_plan(self, plan: RemediationPlan):
        self.plans[plan.id] = plan

    def get_plan(self, plan_id: UUID) -> Optional[RemediationPlan]:
        return self.plans.get(plan_id)

    def get_plans_for_incident(self, incident_id: UUID) -> List[RemediationPlan]:
        plans = [plan for plan in self.plans.values() if plan.incident_id == incident_id]
        return sorted(plans, key=lambda item: item.revision)

    def save_report(self, report: PostIncidentReport):
        self.reports[report.id] = report
        
    def get_reports(self) -> List[PostIncidentReport]:
        return list(self.reports.values())

    def get_report(self, report_id: UUID) -> Optional[PostIncidentReport]:
        return self.reports.get(report_id)

    def save_audit_event(self, event: AuditEvent):
        self.audit_events[event.id] = event

    def get_audit_events(self, incident_id: Optional[UUID] = None) -> List[AuditEvent]:
        events = self.audit_events.values()
        if incident_id is not None:
            events = [event for event in events if event.incident_id == incident_id]
        return sorted(events, key=lambda item: item.created_at)
