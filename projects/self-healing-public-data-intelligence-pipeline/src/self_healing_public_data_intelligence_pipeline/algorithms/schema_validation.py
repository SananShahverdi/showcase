from typing import Dict, List
from self_healing_public_data_intelligence_pipeline.domain.models import Record, ValidationFailure

def validate_and_quarantine(record: Record, expected_schema: Dict[str, type]) -> List[ValidationFailure]:
    """Validates extracted record against a schema. If invalid, quarantines it."""
    failures = []
    data = record.extracted_data
    
    for key, expected_type in expected_schema.items():
        if key not in data:
            failures.append(ValidationFailure(record_id=record.id, crawl_run_id=record.crawl_run_id, field=key, error_message=f"Missing key: {key}"))
        elif not isinstance(data[key], expected_type):
            try:
                data[key] = expected_type(data[key])
            except (ValueError, TypeError):
                 failures.append(ValidationFailure(record_id=record.id, crawl_run_id=record.crawl_run_id, field=key, error_message=f"Invalid type for {key}. Expected {expected_type.__name__}"))
    
    if failures:
        record.is_valid = False
        record.quarantined = True
        
    return failures
