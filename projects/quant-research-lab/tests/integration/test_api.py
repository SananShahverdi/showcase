import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from quant_research_lab.api.app import create_app
from quant_research_lab.services.lab_service import LabService


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(LabService())) as test_client:
        yield test_client


def csv_text(n=400):
    rng = np.random.default_rng(9)
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 50 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    return "Date,Close,Volume\n" + "\n".join(f"{d.date()},{c:.4f},{1000 + i}" for i, (d, c) in enumerate(zip(dates, close)))


def test_bundled_datasets_are_listed(client):
    datasets = {item["id"]: item for item in client.get("/api/datasets").json()}
    assert datasets["aapl-daily"]["rows"] == 2517
    assert datasets["aapl-daily"]["periods_per_year"] == 252
    assert datasets["btc-daily"]["periods_per_year"] == 365
    assert client.get("/health").json()["status"] == "ok"


def test_upload_forecast_strategy_risk_and_report(client):
    created = client.post("/api/datasets", json={"name": "Synthetic daily", "csv": csv_text()})
    assert created.status_code == 201
    dataset_id = created.json()["id"]

    forecast = client.post("/api/forecast", json={"dataset_id": dataset_id, "min_train": 150, "step": 50})
    assert forecast.status_code == 200
    body = forecast.json()
    assert [row["model"] for row in body["scores"]][0] == "random_walk"
    assert body["evaluation"]["test_rows"] > 100

    backtest = client.post("/api/strategy", json={"dataset_id": dataset_id, "cost_bps": 20})
    assert backtest.status_code == 200
    assert set(backtest.json()["strategy"]) >= {"sharpe", "max_drawdown", "trades"}
    assert len(backtest.json()["equity"]) <= 400

    risk = client.get(f"/api/risk/{dataset_id}").json()
    assert risk["var_95"]["historical_var"] > 0
    assert 0 <= risk["garch"]["persistence"] < 1

    report = client.get(f"/api/report/{dataset_id}")
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("text/markdown")
    assert "Diebold-Mariano" in report.text and "not investment advice" in report.text


def test_repeated_runs_are_cached_and_identical(client):
    payload = {"dataset_id": "btc-daily", "cost_bps": 10}
    assert client.post("/api/strategy", json=payload).json() == client.post("/api/strategy", json=payload).json()


def test_errors_are_explicit(client):
    assert client.get("/api/risk/missing").status_code == 404
    assert client.post("/api/forecast", json={"dataset_id": "missing"}).status_code == 404
    assert client.post("/api/forecast", json={"dataset_id": "aapl-daily", "models": ["oracle"]}).status_code == 422
    assert client.post("/api/strategy", json={"dataset_id": "aapl-daily", "cost_bps": -1}).status_code == 422
    bad = client.post("/api/datasets", json={"name": "Bad", "csv": "x,y\n1,2"})
    assert bad.status_code == 422 and "date column" in bad.json()["detail"]
