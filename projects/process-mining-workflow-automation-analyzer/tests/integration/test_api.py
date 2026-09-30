from fastapi.testclient import TestClient
from process_mining_workflow_automation_analyzer.api.app import app

client = TestClient(app)

def test_full_analyzer_flow():
    # 1. Health
    assert client.get("/health").status_code == 200
    
    # 2. Analyze events
    events = [
        {"case_id": "c1", "activity": "A", "timestamp": "2023-01-01T10:00:00Z"},
        {"case_id": "c1", "activity": "B", "timestamp": "2023-01-03T10:00:00Z"}, # 48 hr delay
        {"case_id": "c1", "activity": "C", "timestamp": "2023-01-03T10:05:00Z"},
        {"case_id": "c1", "activity": "B", "timestamp": "2023-01-03T10:10:00Z"}, # rework
        
        {"case_id": "c2", "activity": "A", "timestamp": "2023-01-01T10:00:00Z"},
        {"case_id": "c2", "activity": "C", "timestamp": "2023-01-01T10:05:00Z"}
    ]
    
    resp_analyze = client.post("/api/analyze", json=events)
    assert resp_analyze.status_code == 200
    report = resp_analyze.json()
    
    # Acceptance criteria checks
    assert report["total_cases"] == 2
    assert len(report["variants"]) == 2
    assert len(report["bottlenecks"]) == 1 # A -> B
    assert len(report["rework_loops"]) == 1 # B
    assert len(report["recommendations"]) == 3 # bottleneck, rework, and SLA evidence
    assert "A" in report["recommendations"][0]["title"]
    assert any("activities=B" in evidence for rec in report["recommendations"] for evidence in rec["evidence"])
    assert report["sla_breaches"][0]["case_id"] == "c1"
    
    report_id = report["id"]
    
    # 3. Export to Markdown
    resp_export = client.get(f"/api/export/{report_id}")
    assert resp_export.status_code == 200
    md = resp_export.json()["markdown"]
    assert "Process Mining Report" in md
    assert "**Cases**: 2" in md
    assert "**Events**: 6" in md
    assert "Reduce delay: A → B" in md
    assert "P95 seconds" in md

    issues = client.get(f"/api/export/{report_id}?format=issues")
    assert issues.status_code == 200
    assert len(issues.json()["issues"]) == 3


def test_csv_and_xes_import_share_the_analysis_pipeline():
    csv_content = "case_id,activity,timestamp,resource\nc1,Start,2026-01-01T00:00:00Z,intake\nc1,Done,2026-01-01T01:00:00Z,ops\nbad,,not-a-date,ops\n"
    csv_response = client.post("/api/import/csv", json={"content": csv_content})
    assert csv_response.status_code == 200
    csv_report = csv_response.json()
    assert csv_report["total_events"] == 2
    assert csv_report["data_quality"]["rejected_rows"] == 1

    xes_content = """<log><trace><string key="concept:name" value="x1"/><event><string key="concept:name" value="Start"/><date key="time:timestamp" value="2026-01-01T00:00:00Z"/></event><event><string key="concept:name" value="Done"/><date key="time:timestamp" value="2026-01-01T00:05:00Z"/></event></trace></log>"""
    xes_response = client.post("/api/import/xes", json={"content": xes_content})
    assert xes_response.status_code == 200
    assert xes_response.json()["total_events"] == 2

    unsafe = client.post("/api/import/xes", json={"content": "<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]><log/>"})
    assert unsafe.status_code == 400


def test_spreadsheet_csv_bom_is_accepted_and_parser_errors_are_explained():
    response = client.post("/api/import/csv", json={
        "content": "\ufeffcase_id,activity,timestamp\nc1,Start,2026-09-07T10:00:00Z\n",
    })
    assert response.status_code == 200
    assert response.json()["total_events"] == 1
    malformed = client.post("/api/import/csv", json={
        "content": "case_id,activity,timestamp\nc1," + "A" * 140_000 + ",2026-09-07T10:00:00Z\n",
    })
    assert malformed.status_code == 400
    assert "CSV" in malformed.json()["detail"]


def test_xes_lifecycle_events_are_preserved_during_deduplication():
    content = '<log><trace><string key="concept:name" value="c1"/>'
    for lifecycle in ("start", "complete"):
        content += (
            '<event><string key="concept:name" value="Review"/>'
            '<date key="time:timestamp" value="2026-09-07T10:00:00Z"/>'
            f'<string key="lifecycle:transition" value="{lifecycle}"/></event>'
        )
    response = client.post("/api/import/xes", json={"content": content + "</trace></log>"})
    assert response.status_code == 200
    assert response.json()["total_events"] == 2
    assert response.json()["data_quality"]["duplicate_events"] == 0


def test_demo_seed_analyzes_the_synthetic_log_and_is_listed():
    from process_mining_workflow_automation_analyzer.demo import DEMO_CSV

    seeded = client.post("/api/demo/seed")
    assert seeded.status_code == 200
    report = seeded.json()
    assert (report["total_cases"], report["total_events"]) == (3, len(DEMO_CSV.splitlines()) - 1)
    assert report["data_quality"]["rejected_rows"] == 0
    assert [breach["case_id"] for breach in report["sla_breaches"]] == ["ORD-1042"]
    assert report["rework_loops"] == ["Credit review"]
    assert "24-hour bottleneck threshold" in report["ai_summary"]
    assert "24-hour SLA" in report["ai_summary"]
    assert client.get("/api/reports").json()[0]["id"] == report["id"]
