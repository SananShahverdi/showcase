"""Built-in offline analyzers for changed lines in a unified diff."""

from dataclasses import dataclass
import hashlib
import re
from typing import List

from ai_code_review_test_gatekeeper.domain.models import AnalysisResult, Finding, PullRequest, Severity
from ai_code_review_test_gatekeeper.algorithms.policy_engine import PolicyEngine


@dataclass(frozen=True)
class ChangedLine:
    path: str
    number: int
    content: str


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_added_lines(diff: str) -> List[ChangedLine]:
    """Map added lines to new-file coordinates, including multi-file diffs.

    Plain snippets are accepted for the local form and mapped to ``snippet.txt``.
    """
    if "@@ " not in diff and "diff --git " not in diff:
        return [ChangedLine("snippet.txt", number, content) for number, content in enumerate(diff.splitlines(), 1)]

    result: List[ChangedLine] = []
    path = "unknown"
    new_line: int | None = None
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            candidate = raw[4:].strip()
            path = candidate[2:] if candidate.startswith("b/") else candidate
            continue
        match = HUNK.match(raw)
        if match:
            new_line = int(match.group(1))
            continue
        if new_line is None or raw.startswith("\\ No newline"):
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            result.append(ChangedLine(path, new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        else:
            new_line += 1
    return result


def _finding(tool: str, rule_id: str, category: str, line: ChangedLine, message: str, severity: Severity, remediation: str) -> Finding:
    digest = hashlib.sha256(f"{rule_id}:{line.path}:{line.number}:{line.content.strip()}".encode()).hexdigest()[:16]
    return Finding(
        tool=tool,
        rule_id=rule_id,
        category=category,
        file_path=line.path,
        line_number=line.number,
        end_line=line.number,
        message=message,
        severity=severity,
        remediation=remediation,
        fingerprint=digest,
    )


class StaticAnalyzer:
    @staticmethod
    def analyze(pr: PullRequest) -> AnalysisResult:
        lines = parse_added_lines(pr.diff_content)
        findings: List[Finding] = []
        tests_passed = pr.reported_tests_passed

        for line in lines:
            content = line.content
            if re.search(r"\beval\s*\(", content):
                findings.append(_finding("builtin-semgrep", "python.lang.security.eval", "security", line, "Dynamic eval can execute attacker-controlled code", Severity.CRITICAL, "Use a typed parser or an explicit operation allowlist."))
            if re.search(r"\bpickle\.loads?\s*\(", content) or re.search(r"\byaml\.load\s*\((?![^)]*SafeLoader)", content):
                findings.append(_finding("builtin-semgrep", "python.lang.security.unsafe-deserialization", "security", line, "Deserializing untrusted data can execute arbitrary code", Severity.CRITICAL, "Use a data-only format such as JSON, or yaml.safe_load for YAML."))
            if "console.log" in content:
                findings.append(_finding("builtin-eslint", "javascript.no-console", "quality", line, "Debug logging was added to production code", Severity.WARNING, "Use the structured application logger or remove the statement."))
            if re.search(r"(?i)(password|secret|api_key)\s*=\s*['\"][^'\"]+", content) or re.search(r"AKIA[0-9A-Z]{16}", content):
                findings.append(_finding("builtin-secret-scan", "secret.hardcoded-credential", "secret", line, "Possible hard-coded credential in the diff", Severity.CRITICAL, "Revoke the credential and load it from the approved secret store."))
            if re.search(r"(?i)requests\s*==\s*2\.(?:19|20)\.", content):
                findings.append(_finding("builtin-osv", "dependency.requests.outdated", "dependency", line, "Pinned requests release is outside the supported security baseline", Severity.CRITICAL, "Upgrade requests to the repository-approved current version."))
            if "pytest.fail" in content or "TEST_FAILURE" in content:
                tests_passed = False
                findings.append(_finding("test-runner", "tests.failed", "test", line, "Reported test failure marker found", Severity.CRITICAL, "Fix the failing test and rerun the review."))

        # Stable fingerprints make overlap and repeat-run deduplication explicit.
        deduplicated = {finding.fingerprint: finding for finding in findings}
        return AnalysisResult(
            findings=list(deduplicated.values()),
            tests_passed=tests_passed,
            coverage_percent=pr.reported_coverage_percent,
            changed_files=sorted({line.path for line in lines}),
            tool_statuses={
                "static": _tool_status(findings, {"security", "quality"}),
                "secret": _tool_status(findings, {"secret"}),
                "dependency": _tool_status(findings, {"dependency"}),
                "tests": "passed" if tests_passed else "failed",
                "coverage": "passed" if pr.reported_coverage_percent >= PolicyEngine.MINIMUM_COVERAGE else "warning",  # low coverage requests changes; it does not block
            },
        )


def _tool_status(findings: List[Finding], categories: set[str]) -> str:
    """Summarize one analyzer: failed on a critical finding, warning on warnings only."""
    severities = {finding.severity for finding in findings if finding.category in categories}
    if Severity.CRITICAL in severities:
        return "failed"
    return "warning" if Severity.WARNING in severities else "passed"
