import asyncio
import httpx
from ai_code_review_test_gatekeeper.api.app import app

class ASGIClient:
    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as session:
                return await session.request(method, path, **kwargs)
        return asyncio.run(send())
    def get(self, path, **kwargs): return self.request("GET", path, **kwargs)
    def post(self, path, **kwargs): return self.request("POST", path, **kwargs)

client = ASGIClient()

def test_full_review_flow():
    # 1. Health
    assert client.get("/health").status_code == 200
    
    # 2. Analyze clean PR
    clean_pr = {
        "id": "pr-100",
        "repo": "user/repo",
        "title": "Clean update",
        "diff_content": "def clean():\n    return True"
    }
    resp1 = client.post("/api/reviews/local", json=clean_pr)
    assert resp1.status_code == 200
    report1 = resp1.json()
    assert report1["status"] == "approved"
    
    # 3. Analyze PR with missing tests and critical finding
    bad_pr = {
        "id": "pr-101",
        "repo": "user/repo",
        "title": "Add feature",
        "head_sha": "abc123",
        "diff_content": """diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -1 +1,3 @@
+def new_feature():
+    eval('user_input')
+    console.log('test')
"""
    }
    resp2 = client.post("/api/webhook/pr", json=bad_pr)
    assert resp2.status_code == 200
    report2 = resp2.json()
    assert report2["status"] == "blocked"
    assert len(report2["analysis_result"]["findings"]) == 2
    
    # Check LLM comments for grounding (file and lines)
    assert len(report2["llm_comments"]) > 0
    assert any(c["file_path"] == "src/main.py" for c in report2["llm_comments"])
    assert all(c["file_path"] == "src/main.py" for c in report2["llm_comments"])
    assert {c["line_range"] for c in report2["llm_comments"]} >= {"1", "2", "3"}
    
    # 4. Check dashboard
    resp_dash = client.get("/api/dashboard/reports")
    assert resp_dash.status_code == 200
    reports = resp_dash.json()
    assert len(reports) == 2

    # Duplicate delivery for the same head returns the same report.
    duplicate = client.post("/api/reviews/local", json=bad_pr).json()
    assert duplicate["id"] == report2["id"]

    critical = client.get("/api/dashboard/reports", params={"severity": "critical"}).json()
    assert [item["id"] for item in critical] == [report2["id"]]
    summary = client.get("/api/dashboard/summary", params={"repo": "user/repo"}).json()
    assert summary["total_reviews"] == 2
    assert summary["blocked"] == 1
    assert summary["pass_rate"] == 0.5

def test_coverage_policy_and_input_limit():
    response = client.post("/api/reviews/local", json={
        "id": "pr-low-coverage", "repo": "user/quality", "title": "quality",
        "diff_content": "+const value = 1", "reported_coverage_percent": 72
    })
    assert response.status_code == 200
    assert response.json()["status"] == "changes_requested"
    assert "below" in response.json()["policy_reasons"][0]


def test_reports_keep_title_and_timezone_and_dedupe_without_head_sha():
    payload = {"id": "pr-tz", "repo": "user/tz", "title": "Timezone-safe report", "diff_content": "value = 1"}
    first = client.post("/api/reviews/local", json=payload).json()
    assert first["title"] == "Timezone-safe report"
    # An explicit offset lets browsers render the review time correctly.
    assert first["created_at"].endswith(("Z", "+00:00"))
    assert client.post("/api/reviews/local", json=payload).json()["id"] == first["id"]
    changed = client.post("/api/reviews/local", json={**payload, "reported_coverage_percent": 40}).json()
    assert changed["id"] != first["id"] and changed["status"] == "changes_requested"


def test_empty_diff_is_rejected():
    response = client.post("/api/reviews/local", json={"id": "pr-empty", "repo": "user/empty", "title": "empty", "diff_content": "   "})
    assert response.status_code == 422
