import html
import re
import time
import unicodedata
from typing import Callable, Optional, Sequence
from uuid import UUID

from ai_security_playground_llm_applications.algorithms.tools import SyntheticToolSandbox
from ai_security_playground_llm_applications.domain.models import (
    AppMode, DecisionEffect, ExecutionResult, ScenarioType, SecurityDecision, UserRole,
)


INJECTION_PATTERNS = (
    r"\bignore\s+(all\s+|the\s+)?previous\s+instructions?\b",
    r"\bsystem\s+instruction\b",
    r"\bexecute\s+(?:the\s+)?hidden\s+command\b",
    r"\breveal\s+(?:the\s+)?(?:hidden|system)\s+prompt\b",
)


def canonicalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def contains_injection(value: str) -> bool:
    normalized = canonicalize(value).casefold()
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in INJECTION_PATTERNS)


ACTIVE_MARKUP = re.compile(r"<\s*/?\s*(?:script|iframe|object|embed|svg|img|link|meta|style)\b|\bon[a-z]+\s*=|javascript\s*:", re.IGNORECASE)


def contains_active_markup(value: str) -> bool:
    return bool(ACTIVE_MARKUP.search(canonicalize(value)))


class VulnerableApp:
    @staticmethod
    def execute(
        scenario: ScenarioType,
        payload: str,
        role: UserRole = UserRole.LEARNER,
        allowed_tools: Optional[Sequence[str]] = None,
    ) -> ExecutionResult:
        """Run the intentionally unsafe path. The verdict reflects whether this input
        actually achieved the attack; a benign payload is answered but not counted."""
        start = time.perf_counter()
        output, tools, requested, effect = "", [], [], None
        succeeded = True
        if scenario == ScenarioType.DIRECT_INJECTION:
            succeeded = contains_injection(payload)
            output = f"Executed untrusted instruction: {payload}" if succeeded else f"Answered: {payload}"
        elif scenario == ScenarioType.INDIRECT_INJECTION:
            requested = tools = ["file_lookup"]
            content = SyntheticToolSandbox.unsafe_file_lookup("poisoned-policy.txt")
            output = f"Retrieved: {content} Hidden command followed."
        elif scenario == ScenarioType.INSECURE_OUTPUT:
            output = payload
            succeeded = contains_active_markup(payload)
        elif scenario == ScenarioType.DATA_LEAKAGE:
            requested = tools = ["file_lookup"]
            output = SyntheticToolSandbox.unsafe_file_lookup(payload)
            succeeded = output == SyntheticToolSandbox.SECRET_FIXTURE
        elif scenario == ScenarioType.EXCESSIVE_AGENCY:
            succeeded = SyntheticToolSandbox.is_mutation(payload)
            requested = tools = ["sql_write"] if succeeded else ["sql_read"]
            output = SyntheticToolSandbox.unsafe_sql(payload)
            effect = "synthetic_only: database mutation" if succeeded else None
        elif scenario == ScenarioType.WEAK_TOOL_PERMISSIONS:
            requested = tools = ["create_ticket"]
            output = SyntheticToolSandbox.create_ticket("P1 Production outage")
            effect = "synthetic_only: ticket creation"
            # Creating the ticket is only an escalation when the caller's role lacks the tool.
            succeeded = allowed_tools is None or "create_ticket" not in allowed_tools
        return ExecutionResult(
            query=payload, mode=AppMode.VULNERABLE, scenario_type=scenario, role=role,
            was_successful_attack=succeeded, tools_called=tools, requested_tools=requested,
            output=output, synthetic_effect=effect,
            decisions=[SecurityDecision(control_id="VULN-UNTRUSTED-AUTO", effect=DecisionEffect.ALLOW,
                                        reason="Training mode intentionally bypassed controls inside the synthetic sandbox")],
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class HardenedApp:
    @staticmethod
    def execute(
        scenario: ScenarioType,
        payload: str,
        role: UserRole = UserRole.LEARNER,
        create_approval: Optional[Callable[[ExecutionResult], UUID]] = None,
        allowed_tools: Optional[Sequence[str]] = None,
    ) -> ExecutionResult:
        start = time.perf_counter()
        payload = canonicalize(payload)
        decisions = []
        tools, requested, controls = [], [], []
        output = "Request handled safely."
        approval_needed = False

        if scenario == ScenarioType.DIRECT_INJECTION:
            if contains_injection(payload):
                controls = ["INPUT-001"]
                decisions.append(SecurityDecision(control_id="INPUT-001", effect=DecisionEffect.BLOCK,
                                                  reason="Instruction-override pattern detected after canonicalization"))
                output = "Blocked: prompt-injection policy matched untrusted input."
        elif scenario == ScenarioType.INDIRECT_INJECTION:
            requested = ["file_lookup"]
            content = SyntheticToolSandbox.safe_file_lookup("poisoned-policy.txt")
            if contains_injection(content):
                controls = ["RAG-002"]
                decisions.append(SecurityDecision(control_id="RAG-002", effect=DecisionEffect.BLOCK,
                                                  reason="Retrieved content contained agent-directed instructions"))
                output = "Blocked: poisoned retrieval content was quarantined."
            else:
                tools = ["file_lookup"]
        elif scenario == ScenarioType.INSECURE_OUTPUT:
            controls = ["OUTPUT-001"]
            decisions.append(SecurityDecision(control_id="OUTPUT-001", effect=DecisionEffect.SANITIZE,
                                              reason="Untrusted output was HTML-encoded for text rendering"))
            output = html.escape(payload, quote=True)
        elif scenario == ScenarioType.DATA_LEAKAGE:
            requested = ["file_lookup"]
            controls = ["TOOL-PATH-001"]
            decisions.append(SecurityDecision(control_id="TOOL-PATH-001", effect=DecisionEffect.BLOCK,
                                              reason="Absolute and host-style paths are outside the virtual store"))
            output = "Permission denied: only allowlisted virtual documents can be read."
        elif scenario == ScenarioType.EXCESSIVE_AGENCY and not SyntheticToolSandbox.is_mutation(payload):
            requested = ["sql_read"]
            try:
                output = SyntheticToolSandbox.safe_sql(payload)
                tools = ["sql_read"]
            except PermissionError as exc:
                controls = ["SQL-READONLY-001"]
                decisions.append(SecurityDecision(control_id="SQL-READONLY-001", effect=DecisionEffect.BLOCK, reason=str(exc)))
                output = "Blocked: only one read-only SELECT statement is allowed."
        elif scenario == ScenarioType.EXCESSIVE_AGENCY:
            requested = ["sql_write"]
            controls = ["SQL-READONLY-001", "APPROVAL-001"]
            decisions.append(SecurityDecision(control_id="SQL-READONLY-001", effect=DecisionEffect.BLOCK,
                                              reason="Destructive SQL is outside the read-only tool contract"))
            decisions.append(SecurityDecision(control_id="APPROVAL-001", effect=DecisionEffect.REQUIRE_APPROVAL,
                                              reason="A security administrator must explicitly approve this synthetic action"))
            output = "Approval required: destructive action was not executed."
            approval_needed = True
        elif scenario == ScenarioType.WEAK_TOOL_PERMISSIONS:
            requested = ["create_ticket"]
            if allowed_tools is not None and "create_ticket" in allowed_tools:
                # Authorized by the role/tool matrix, but an external write still needs a human.
                controls = ["APPROVAL-002"]
                decisions.append(SecurityDecision(control_id="RBAC-001", effect=DecisionEffect.ALLOW,
                                                  reason=f"Role {role.value} may request external tickets"))
                decisions.append(SecurityDecision(control_id="APPROVAL-002", effect=DecisionEffect.REQUIRE_APPROVAL,
                                                  reason="External writes run only after explicit one-time approval"))
                output = "Approval required: the ticket was not created yet."
                approval_needed = True
            else:
                controls = ["RBAC-001"]
                decisions.append(SecurityDecision(control_id="RBAC-001", effect=DecisionEffect.BLOCK,
                                                  reason=f"Role {role.value} is not allowed to create external tickets"))
                output = "Permission denied: this role cannot create tickets."

        result = ExecutionResult(
            query=payload, mode=AppMode.HARDENED, scenario_type=scenario, role=role,
            was_successful_attack=False, tools_called=tools, requested_tools=requested,
            output=output, mitigation_triggered=bool(controls), controls_triggered=controls,
            decisions=decisions, duration_ms=round((time.perf_counter() - start) * 1000, 3),
        )
        if approval_needed and create_approval:
            result.approval_id = create_approval(result)
        return result
