from datetime import datetime, timedelta
from uuid import uuid4
from self_healing_public_data_intelligence_pipeline.domain.models import Record
from self_healing_public_data_intelligence_pipeline.algorithms.locator_ranking import rank_locators
from self_healing_public_data_intelligence_pipeline.algorithms.schema_validation import validate_and_quarantine
from self_healing_public_data_intelligence_pipeline.algorithms.dom_fingerprinting import compute_dom_fingerprint, detect_drift
from self_healing_public_data_intelligence_pipeline.algorithms.anomaly_detection import detect_freshness_anomaly
from self_healing_public_data_intelligence_pipeline.algorithms.recipe_scoring import score_recipe
from self_healing_public_data_intelligence_pipeline.services.pipeline_service import extract_records

def test_locator_ranking():
    locators = [
        {"type": "css", "value": "div > div > span"}, # positional -> score 0
        {"type": "css", "value": "#main-title"}, # semantic -> score 2
        {"type": "css", "value": "[aria-label='price']"} # accessibility -> score 3
    ]
    ranked = rank_locators(locators)
    assert "aria-label" in ranked[0]["value"]
    assert "#main-title" in ranked[1]["value"]
    assert "div > div" in ranked[2]["value"]

def test_schema_validation():
    expected_schema = {"title": str, "price": float}
    
    # Valid
    valid_record = Record(crawl_run_id=uuid4(), extracted_data={"title": "Test", "price": 10.5})
    failures = validate_and_quarantine(valid_record, expected_schema)
    assert len(failures) == 0
    assert valid_record.is_valid == True
    
    # Invalid type
    invalid_record = Record(crawl_run_id=uuid4(), extracted_data={"title": "Test", "price": "not_a_float"})
    failures = validate_and_quarantine(invalid_record, expected_schema)
    assert len(failures) == 1
    assert invalid_record.is_valid == False
    assert invalid_record.quarantined == True
    
    # Missing key
    missing_record = Record(crawl_run_id=uuid4(), extracted_data={"title": "Test"})
    failures = validate_and_quarantine(missing_record, expected_schema)
    assert len(failures) == 1

def test_dom_fingerprinting():
    html1 = "<html><body><h1>Hello</h1></body></html>"
    html2 = "<html><body class='dark'><h1>Hello</h1></body></html>"
    html_drift = "<html><body><div><h1>Hello</h1></div></body></html>"
    
    assert detect_drift(html1, html2) == False # Classes don't change structure
    assert detect_drift(html1, html_drift) == True # Div added

def test_recipe_scoring():
    assert score_recipe(10, 0) == 1.0
    assert score_recipe(5, 5) == 0.5
    assert score_recipe(0, 10) == 0.0

def test_anomaly_detection():
    now = datetime.utcnow()
    # 2 hours ago
    t1 = now - timedelta(hours=2)
    assert detect_freshness_anomaly([t1], now, max_allowed_gap_seconds=86400) == False
    
    # 2 days ago
    t2 = now - timedelta(days=2)
    assert detect_freshness_anomaly([t2], now, max_allowed_gap_seconds=86400) == True


def test_real_css_extraction_supports_repeating_records_and_attributes():
    html = "<article><h2>A</h2><meta itemprop='price' content='2.5'></article><article><h2>B</h2><meta itemprop='price' content='3.0'></article>"
    records = extract_records(html, {"_record": "article", "title": "h2", "price": "[itemprop='price']@content"})
    assert records == [{"title": "A", "price": "2.5"}, {"title": "B", "price": "3.0"}]
