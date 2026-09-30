import os
from datetime import datetime, timezone

from network_digital_twin_rl_routing_optimizer.domain.models import SimulationMetrics, TrainingResult


class TrainingService:
    """Always-on local experiment registry with an optional MLflow sink."""

    def __init__(self):
        self.experiments = []

    def log_training(self, result: TrainingResult):
        self.experiments.append({
            "run_name": f"train-{result.policy_version}",
            "kind": "training",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": result.model_dump(mode="json"),
        })

    def log_experiment(self, run_name: str, metrics: SimulationMetrics):
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if tracking_uri:
            import mlflow
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment("Routing_Optimization")
            with mlflow.start_run(run_name=run_name):
                mlflow.log_params({"algorithm": metrics.algorithm.value, "seed": metrics.seed})
                mlflow.log_metrics({
                    "delivered_packets": metrics.delivered_packets,
                    "dropped_packets": metrics.dropped_packets,
                    "avg_latency_ms": metrics.avg_latency_ms,
                    "p95_latency_ms": metrics.p95_latency_ms,
                })
        self.experiments.append({
            "run_name": run_name,
            "kind": "evaluation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics.model_dump(mode="json"),
            "external_tracking": bool(tracking_uri),
        })

    def get_experiments(self) -> list:
        return list(reversed(self.experiments))

    def reset(self):
        self.experiments.clear()
