from aiops_incident_assistant_human_approval.algorithms.policy_engine import PolicyEngine
from aiops_incident_assistant_human_approval.algorithms.ai_agent import AIOpsAgent
from aiops_incident_assistant_human_approval.domain.models import Incident, IncidentType, TelemetryData
from aiops_incident_assistant_human_approval.adapters.executor import LocalSafeExecutor

def test_policy_engine():
    assert PolicyEngine.is_action_allowed("kubectl get pods") is True
    assert PolicyEngine.is_action_allowed("rm -rf /var/log/*") is False
    assert PolicyEngine.is_action_allowed("DROP TABLE users;") is False
    assert PolicyEngine.is_action_allowed("chmod 777 /etc/passwd") is False

def test_ai_agent_plan_generation():
    inc1 = Incident(type=IncidentType.LATENCY_SPIKE, service_name="api", telemetry=TelemetryData())
    plan1 = AIOpsAgent.analyze_incident(inc1)
    assert len(plan1.actions) == 1
    assert plan1.actions[0].risk_level == "medium"
    assert {item.kind for item in plan1.evidence} == {"metric", "log", "trace", "runbook"}
    assert plan1.runbook.endswith("database-pool-saturation.md")
    
    inc2 = Incident(type=IncidentType.QUEUE_BACKLOG, service_name="worker", telemetry=TelemetryData())
    plan2 = AIOpsAgent.analyze_incident(inc2)
    assert len(plan2.actions) == 2

def test_local_executor_never_accepts_arbitrary_shell_commands():
    executor = LocalSafeExecutor()
    assert executor.execute("kubectl rollout restart deployment/worker").succeeded is True
    denied = executor.execute("echo approved && rm -rf /")
    assert denied.succeeded is False
    assert "Denied" in denied.output
