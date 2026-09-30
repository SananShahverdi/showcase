from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeviceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TelemetryData(BaseModel):
    timestamp: datetime
    link_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$")
    device_id: str = Field(default="unknown", min_length=1, max_length=120)
    utilization_mbps: float = Field(ge=0)
    capacity_mbps: float = Field(gt=0)
    latency_ms: float = Field(ge=0)
    packet_loss_pct: float = Field(ge=0, le=100)
    throughput_mbps: Optional[float] = Field(default=None, ge=0)
    traffic_class: str = Field(default="aggregate", min_length=1, max_length=80)
    device_health: DeviceHealth = DeviceHealth.HEALTHY

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_operating_range(self) -> "TelemetryData":
        if self.utilization_mbps > self.capacity_mbps * 5:
            raise ValueError("utilization_mbps cannot exceed five times capacity_mbps")
        if self.throughput_mbps is not None and self.throughput_mbps > self.capacity_mbps * 5:
            raise ValueError("throughput_mbps cannot exceed five times capacity_mbps")
        return self


class IngestionSummary(BaseModel):
    received_count: int
    accepted_count: int
    duplicate_count: int
    affected_links: List[str]


class ForecastPoint(BaseModel):
    timestamp: datetime
    predicted_mbps: float = Field(ge=0)
    lower_bound_mbps: float = Field(ge=0)
    upper_bound_mbps: float = Field(ge=0)


class ForecastDiagnostics(BaseModel):
    method: str
    sample_count: int
    horizon_days: int
    slope_mbps_per_day: float
    mean_absolute_error_mbps: float
    confidence_level_pct: float = 95.0
    warnings: List[str] = Field(default_factory=list)


class RiskScore(BaseModel):
    link_id: str
    saturation_probability_pct: float = Field(ge=0, le=100)
    estimated_days_to_saturation: Optional[int] = Field(default=None, ge=1)
    risk_level: RiskLevel
    current_headroom_pct: float
    threshold_mbps: float = Field(gt=0)
    reasons: List[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    id: str
    action: str
    description: str
    cost_estimate_usd: float = Field(ge=0)
    capacity_gain_mbps: float = Field(ge=0)
    priority: int = Field(ge=1, le=5)
    impact: str
    selected: bool = True
    selection_reason: str


class ForecastResult(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    link_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    capacity_mbps: float = Field(gt=0)
    historical_data: List[TelemetryData] = Field(default_factory=list)
    forecast_points: List[ForecastPoint] = Field(default_factory=list)
    diagnostics: ForecastDiagnostics
    risk: RiskScore
    recommendations: List[Recommendation] = Field(default_factory=list)


class WhatIfScenario(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=120)
    traffic_growth_multiplier: float = Field(default=1.0, ge=0, le=5)
    traffic_reduction_pct: float = Field(default=0, ge=0, le=95)
    added_capacity_mbps: float = Field(default=0, ge=0)
    budget_usd: Optional[float] = Field(default=None, ge=0)
    forecast_days: int = Field(default=90, ge=7, le=90)
    created_at: datetime = Field(default_factory=utc_now)
    forecast: Optional[ForecastResult] = None
    baseline_risk_level: Optional[RiskLevel] = None
    risk_reduction_pct: Optional[float] = None
    headroom_delta_pct: Optional[float] = None


class LinkSummary(BaseModel):
    link_id: str
    device_id: str
    latest_timestamp: datetime
    sample_count: int
    utilization_mbps: float
    capacity_mbps: float
    utilization_pct: float
    latency_ms: float
    packet_loss_pct: float
    device_health: DeviceHealth
    stale: bool
    data_quality_warnings: List[str] = Field(default_factory=list)


class PortfolioOverview(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    link_count: int
    sample_count: int
    stale_link_count: int
    critical_link_count: int
    links: List[LinkSummary]


class WeeklyCapacityReport(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    reporting_window_days: int = 7
    assumptions: List[str]
    overview: PortfolioOverview
    forecasts: List[ForecastResult]

