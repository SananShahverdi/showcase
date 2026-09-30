from collections import Counter
import hashlib
from typing import Dict, List
from uuid import UUID

from ai_code_review_test_gatekeeper.algorithms.analyzers import StaticAnalyzer
from ai_code_review_test_gatekeeper.algorithms.llm_reviewer import LLMReviewer
from ai_code_review_test_gatekeeper.algorithms.policy_engine import PolicyEngine
from ai_code_review_test_gatekeeper.domain.models import DashboardSummary, PullRequest, ReviewReport, ReviewStatus, Severity


class ReviewRepository:
    def __init__(self):
        self.reports: Dict[UUID, ReviewReport] = {}
        self.idempotency: Dict[str, UUID] = {}

    def save(self, report: ReviewReport, key: str):
        self.reports[report.id] = report
        self.idempotency[key] = report.id

    def get(self, report_id: UUID) -> ReviewReport | None:
        return self.reports.get(report_id)

    def get_by_key(self, key: str) -> ReviewReport | None:
        report_id = self.idempotency.get(key)
        return self.reports.get(report_id) if report_id else None

    def get_all(self, repo: str | None = None, status: ReviewStatus | None = None, severity: Severity | None = None) -> List[ReviewReport]:
        reports = list(self.reports.values())
        if repo:
            reports = [report for report in reports if report.repo == repo]
        if status:
            reports = [report for report in reports if report.status == status]
        if severity:
            reports = [report for report in reports if any(finding.severity == severity for finding in report.analysis_result.findings)]
        return sorted(reports, key=lambda report: report.created_at, reverse=True)


class ReviewService:
    def __init__(self, repo: ReviewRepository):
        self.repo = repo

    @staticmethod
    def _key(pr: PullRequest) -> str:
        # Without a head SHA, key on a digest of everything that affects the gate.
        # Python's built-in hash() is randomized per process, so it would break
        # deduplication after a restart with persistence enabled.
        evidence = f"{pr.reported_coverage_percent}:{pr.reported_tests_passed}:{pr.diff_content}"
        revision = pr.head_sha or hashlib.sha256(evidence.encode("utf-8")).hexdigest()
        return f"{pr.repo}:{pr.id}:{revision}"

    def analyze_pr(self, pr: PullRequest) -> ReviewReport:
        key = self._key(pr)
        existing = self.repo.get_by_key(key)
        if existing:
            return existing

        analysis = StaticAnalyzer.analyze(pr)
        status, reasons = PolicyEngine.evaluate_with_reasons(analysis)
        summary, comments = LLMReviewer.generate_review(pr, analysis)
        report = ReviewReport(
            pr_id=pr.id,
            repo=pr.repo,
            title=pr.title,
            status=status,
            analysis_result=analysis,
            llm_summary=summary,
            llm_comments=comments,
            policy_reasons=reasons,
        )
        self.repo.save(report, key)
        return report

    def get_report(self, report_id: UUID) -> ReviewReport:
        report = self.repo.get(report_id)
        if report is None:
            raise ValueError("Review report not found")
        return report

    def get_dashboard_data(self, repo: str | None = None, status: ReviewStatus | None = None, severity: Severity | None = None) -> List[ReviewReport]:
        return self.repo.get_all(repo, status, severity)

    def get_summary(self, repo: str | None = None) -> DashboardSummary:
        reports = self.repo.get_all(repo=repo)
        counts = Counter(report.status for report in reports)
        rules = Counter(
            finding.rule_id
            for report in reports
            for finding in report.analysis_result.findings
        )
        total = len(reports)
        approved = counts[ReviewStatus.APPROVED]
        return DashboardSummary(
            total_reviews=total,
            approved=approved,
            changes_requested=counts[ReviewStatus.CHANGES_REQUESTED],
            blocked=counts[ReviewStatus.BLOCKED],
            pass_rate=(approved / total) if total else 0.0,
            recurring_rules=dict(rules.most_common(10)),
        )
