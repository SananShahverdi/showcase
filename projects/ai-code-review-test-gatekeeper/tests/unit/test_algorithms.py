from ai_code_review_test_gatekeeper.algorithms.analyzers import StaticAnalyzer, parse_added_lines
from ai_code_review_test_gatekeeper.algorithms.llm_reviewer import LLMReviewer
from ai_code_review_test_gatekeeper.algorithms.policy_engine import PolicyEngine
from ai_code_review_test_gatekeeper.domain.models import PullRequest, ReviewStatus

def test_static_analyzer():
    diff = """diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -8,2 +8,3 @@
 safe = True
+eval('danger')
+pytest.fail('broken')
"""
    pr = PullRequest(id="1", repo="test/repo", title="feat", diff_content=diff)
    res = StaticAnalyzer.analyze(pr)
    
    assert res.tests_passed is False
    assert any(f.tool == "builtin-semgrep" and f.severity == "critical" for f in res.findings)
    assert any(f.tool == "test-runner" for f in res.findings)
    eval_finding = next(f for f in res.findings if f.rule_id == "python.lang.security.eval")
    assert eval_finding.file_path == "src/main.py"
    assert eval_finding.line_number == 9
    assert eval_finding.fingerprint

def test_policy_engine():
    pr_pass = PullRequest(id="2", repo="test/repo", title="fix", diff_content="def hello(): pass")
    res_pass = StaticAnalyzer.analyze(pr_pass)
    status_pass = PolicyEngine.evaluate(res_pass)
    assert status_pass == ReviewStatus.APPROVED
    
    pr_fail = PullRequest(id="3", repo="test/repo", title="bad", diff_content="eval('x')")
    res_fail = StaticAnalyzer.analyze(pr_fail)
    status_fail = PolicyEngine.evaluate(res_fail)
    assert status_fail == ReviewStatus.BLOCKED

def test_llm_reviewer():
    pr = PullRequest(id="4", repo="test/repo", title="new feature", diff_content="def new_feature():\n    eval('1')")
    res = StaticAnalyzer.analyze(pr)
    summary, comments = LLMReviewer.generate_review(pr, res)
    
    assert "1 critical" in summary
    assert any("eval" in c.comment for c in comments)
    assert any("without a changed test" in c.comment for c in comments)

def test_diff_parser_ignores_removed_lines_and_maps_multiple_hunks():
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
-eval('removed')
+safe_parse(value)
 context
@@ -10 +10 @@
+console.log('new')
"""
    lines = parse_added_lines(diff)
    assert [(line.path, line.number, line.content) for line in lines] == [
        ("app.py", 1, "safe_parse(value)"),
        ("app.py", 10, "console.log('new')"),
    ]


def test_tool_statuses_reflect_findings_per_analyzer():
    pr = PullRequest(id="5", repo="test/repo", title="mixed", diff_content="password = 'hunter2'\nconsole.log('debug')", reported_coverage_percent=95)
    statuses = StaticAnalyzer.analyze(pr).tool_statuses
    assert statuses == {"static": "warning", "secret": "failed", "dependency": "passed", "tests": "passed", "coverage": "passed"}
    clean = StaticAnalyzer.analyze(PullRequest(id="6", repo="test/repo", title="clean", diff_content="value = 1"))
    assert set(clean.tool_statuses.values()) == {"passed"}


def test_unsafe_deserialization_is_critical_but_safe_yaml_is_not():
    diff = "data = pickle.loads(request.body)\nconfig = yaml.load(stream)\nsafe = yaml.load(stream, Loader=yaml.SafeLoader)"
    findings = StaticAnalyzer.analyze(PullRequest(id="7", repo="test/repo", title="load", diff_content=diff)).findings
    assert sorted(f.line_number for f in findings if f.rule_id == "python.lang.security.unsafe-deserialization") == [1, 2]
    assert all(f.severity == "critical" for f in findings)


def test_blocked_policy_still_reports_advisory_reasons():
    pr = PullRequest(id="8", repo="test/repo", title="bad", diff_content="eval(x)\nconsole.log(x)", reported_coverage_percent=60)
    status, reasons = PolicyEngine.evaluate_with_reasons(StaticAnalyzer.analyze(pr))
    assert status == ReviewStatus.BLOCKED
    assert reasons == ["1 critical finding exceeds policy", "Coverage 60.0% is below 80.0%", "1 warning finding requires review"]


def test_low_coverage_is_a_warning_not_a_failure():
    """Coverage below the minimum requests changes; only critical findings and failing tests block."""
    pr = PullRequest(id="7", repo="test/repo", title="thin tests", diff_content="value = 1", reported_coverage_percent=40)
    assert StaticAnalyzer.analyze(pr).tool_statuses["coverage"] == "warning"
