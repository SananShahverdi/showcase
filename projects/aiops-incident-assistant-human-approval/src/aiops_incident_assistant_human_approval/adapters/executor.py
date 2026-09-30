from dataclasses import dataclass

from aiops_incident_assistant_human_approval.algorithms.policy_engine import PolicyEngine


@dataclass(frozen=True)
class ExecutionResult:
    succeeded: bool
    output: str


class LocalSafeExecutor:
    """A non-shell local adapter for demonstrating approved execution safely."""

    def execute(self, command: str) -> ExecutionResult:
        allowed, reason = PolicyEngine.evaluate(command)
        if not allowed:
            return ExecutionResult(False, reason)
        # Deliberately do not invoke subprocess or a shell.  This adapter proves
        # lifecycle behavior while external cluster access is unavailable.
        return ExecutionResult(True, f"Local safe executor accepted catalog action: {command}")
