class PolicyEngine:
    DANGEROUS_PATTERNS = [
        "rm -rf",
        "drop table",
        "truncate table",
        "shutdown",
        "reboot",
        "chmod 777"
    ]

    ALLOWED_PREFIXES = (
        "kubectl get ",
        "kubectl scale deployment ",
        "kubectl rollout undo deployment/",
        "kubectl rollout restart deployment/",
        "kubectl delete pod -l ",
    )

    @staticmethod
    def evaluate(command: str) -> tuple[bool, str]:
        cmd_lower = command.lower()
        for pattern in PolicyEngine.DANGEROUS_PATTERNS:
            if pattern in cmd_lower:
                return False, f"Denied by dangerous command pattern: {pattern}"
        if any(cmd_lower.startswith(prefix) for prefix in PolicyEngine.ALLOWED_PREFIXES):
            return True, "Allowed by constrained remediation catalog"
        return False, "Denied because the command is outside the remediation catalog"

    @staticmethod
    def is_action_allowed(command: str) -> bool:
        return PolicyEngine.evaluate(command)[0]
