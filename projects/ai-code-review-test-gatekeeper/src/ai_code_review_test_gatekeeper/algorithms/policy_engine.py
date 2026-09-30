from typing import List, Tuple

from ai_code_review_test_gatekeeper.domain.models import AnalysisResult, ReviewStatus, Severity, count_noun


class PolicyEngine:
    MINIMUM_COVERAGE = 80.0

    @staticmethod
    def evaluate_with_reasons(analysis: AnalysisResult) -> Tuple[ReviewStatus, List[str]]:
        """Return the gate decision and every reason behind it.

        Blocking reasons (failed tests, critical findings) decide the status, but
        non-blocking reasons are still reported so a blocked PR lists everything
        the author must fix, not only the first gate that failed.
        """
        blocking: List[str] = []
        if not analysis.tests_passed:
            blocking.append("Required tests failed")
        critical = [finding for finding in analysis.findings if finding.severity == Severity.CRITICAL]
        if critical:
            blocking.append(f"{count_noun(len(critical), 'critical finding')} {'exceeds' if len(critical) == 1 else 'exceed'} policy")
        advisory: List[str] = []
        if analysis.coverage_percent < PolicyEngine.MINIMUM_COVERAGE:
            advisory.append(f"Coverage {analysis.coverage_percent:.1f}% is below {PolicyEngine.MINIMUM_COVERAGE:.1f}%")
        warnings = [finding for finding in analysis.findings if finding.severity == Severity.WARNING]
        if warnings:
            advisory.append(f"{count_noun(len(warnings), 'warning finding')} {'requires' if len(warnings) == 1 else 'require'} review")
        if blocking:
            return ReviewStatus.BLOCKED, blocking + advisory
        if advisory:
            return ReviewStatus.CHANGES_REQUESTED, advisory
        return ReviewStatus.APPROVED, ["All required quality and security gates passed"]

    @staticmethod
    def evaluate(analysis: AnalysisResult) -> ReviewStatus:
        return PolicyEngine.evaluate_with_reasons(analysis)[0]
