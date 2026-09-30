from typing import Dict, Optional
from uuid import UUID
from post_quantum_crypto_migration_scanner.domain.models import ScanReport

class InventoryStore:
    def __init__(self):
        self.reports: Dict[UUID, ScanReport] = {}
        
    def save(self, report: ScanReport):
        self.reports[report.id] = report
        
    def get(self, report_id: UUID) -> Optional[ScanReport]:
        return self.reports.get(report_id)
        
    def get_latest(self) -> Optional[ScanReport]:
        if not self.reports:
            return None
        return sorted(self.reports.values(), key=lambda r: r.scanned_at)[-1]
