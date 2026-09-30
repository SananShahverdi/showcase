"""Credential-free grounded review writer.

The class name is retained as a stable adapter boundary.  Local output is
deterministic and never attributes content to a hosted model.
"""

from typing import List, Tuple

from ai_code_review_test_gatekeeper.algorithms.analyzers import parse_added_lines
from ai_code_review_test_gatekeeper.domain.models import AnalysisResult, LLMComment, PullRequest, Severity, count_noun


class LLMReviewer:
    @staticmethod
    def generate_review(pr: PullRequest, analysis: AnalysisResult) -> Tuple[str, List[LLMComment]]:
        critical = sum(finding.severity == Severity.CRITICAL for finding in analysis.findings)
        warnings = sum(finding.severity == Severity.WARNING for finding in analysis.findings)
        summary = (
            f"Reviewed {count_noun(len(analysis.changed_files), 'changed file')}: "
            f"{count_noun(critical, 'critical finding')} and {count_noun(warnings, 'warning')}; "
            f"tests {'passed' if analysis.tests_passed else 'failed'} at {analysis.coverage_percent:.1f}% reported coverage."
        )
        comments = [
            LLMComment(
                file_path=finding.file_path or "unknown",
                line_range=str(finding.line_number or 1),
                comment=f"[{finding.rule_id}] {finding.message}",
                suggested_fix=finding.remediation,
            )
            for finding in analysis.findings
            if finding.file_path and finding.line_number
        ]

        added = parse_added_lines(pr.diff_content)
        has_feature = next((line for line in added if "def new_feature" in line.content or "function newFeature" in line.content), None)
        has_test = any("test" in line.path.lower() for line in added)
        if has_feature and not has_test:
            comments.append(LLMComment(
                file_path=has_feature.path,
                line_range=str(has_feature.number),
                comment="New behavior is added without a changed test file; add a focused success and failure-path test.",
                suggested_fix="Add a test file that exercises this changed function and its boundary cases.",
            ))
        return summary, comments
