from typing import List
from datetime import datetime

def detect_freshness_anomaly(timestamps: List[datetime], current_time: datetime, max_allowed_gap_seconds: int = 86400) -> bool:
    """Detects when sources stop updating or change update patterns."""
    if not timestamps:
        return False
    
    last_update = max(timestamps)
    gap = (current_time - last_update).total_seconds()
    
    return gap > max_allowed_gap_seconds
