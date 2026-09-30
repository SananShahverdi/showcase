"""API contracts for datasets, forecasting studies, strategy backtests, and risk reports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ModelName = Literal["random_walk", "historical_mean", "ridge", "random_forest", "gradient_boosting"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatasetSummary(BaseModel):
    id: str
    name: str
    source: str
    rows: int
    start: str
    end: str
    periods_per_year: int
    has_volume: bool
    bundled: bool


class DatasetUpload(Strict):
    name: str = Field(min_length=1, max_length=80)
    csv: str = Field(min_length=1, max_length=2_000_000)


class ForecastRequest(Strict):
    dataset_id: str
    min_train: int = Field(default=504, ge=60, le=5000)
    step: int = Field(default=63, ge=5, le=252)
    cost_bps: float = Field(default=5.0, ge=0, le=100)
    models: list[ModelName] = Field(default_factory=lambda: ["random_walk", "historical_mean", "ridge", "random_forest", "gradient_boosting"])


class StrategyRequest(Strict):
    dataset_id: str
    threshold: float = Field(default=0.0, ge=-1, le=1)
    cost_bps: float = Field(default=10.0, ge=0, le=100)
    trend: float = Field(default=0.25, ge=-1, le=1)
    tendency: float = Field(default=0.25, ge=-1, le=1)
    pattern: float = Field(default=0.25, ge=-1, le=1)
    influence: float = Field(default=0.25, ge=-1, le=1)
