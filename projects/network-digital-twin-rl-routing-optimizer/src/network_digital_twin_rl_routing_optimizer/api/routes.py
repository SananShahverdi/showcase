from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from network_digital_twin_rl_routing_optimizer.algorithms.simulator import NetworkSimulator
from network_digital_twin_rl_routing_optimizer.domain.models import NetworkState, RoutingAlgorithm, SimulationMetrics, TopologyType, TrainingResult
from network_digital_twin_rl_routing_optimizer.services.inference_service import InferenceService
from network_digital_twin_rl_routing_optimizer.services.training_service import TrainingService

router = APIRouter()
simulator = NetworkSimulator()
training_service = TrainingService()
inference_service = InferenceService(simulator, training_service)


class BuildTopologyRequest(BaseModel):
    topology: TopologyType
    num_nodes: int = Field(default=5, ge=3, le=100)


class LinkRequest(BaseModel):
    source: str
    target: str


class EvaluateRequest(BaseModel):
    algorithm: RoutingAlgorithm
    num_packets: int = Field(default=100, ge=1, le=100_000)
    seed: int = 42


class TrainRequest(BaseModel):
    episodes: int = Field(default=500, ge=20, le=50_000)
    seed: int = 42


class CompareRequest(BaseModel):
    algorithms: List[RoutingAlgorithm] = Field(default_factory=lambda: [RoutingAlgorithm.DIJKSTRA, RoutingAlgorithm.ECMP, RoutingAlgorithm.RANDOM, RoutingAlgorithm.RL_AGENT], min_length=2)
    num_packets: int = Field(default=100, ge=1, le=100_000)
    seed: int = 42


class RouteRequest(BaseModel):
    algorithm: RoutingAlgorithm
    source: str
    target: str
    seed: int = 42


@router.post("/simulator/topology")
def build_topology(request: BuildTopologyRequest):
    simulator.build_topology(request.topology, request.num_nodes)
    training_service.reset()
    inference_service.reset()
    return {"message": "Topology built", "topology": request.topology, "num_nodes": request.num_nodes}


@router.post("/simulator/fail")
def fail_link(request: LinkRequest):
    try:
        simulator.fail_link(request.source, request.target)
        return {"message": "Link failed", "source": request.source, "target": request.target}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/simulator/recover")
def recover_link(request: LinkRequest):
    try:
        simulator.recover_link(request.source, request.target)
        return {"message": "Link recovered", "source": request.source, "target": request.target}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/simulator/state", response_model=NetworkState)
def get_state():
    return simulator.state


@router.post("/train", response_model=TrainingResult)
def train_policy(request: TrainRequest):
    try:
        return inference_service.train_policy(request.episodes, request.seed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/route")
def route(request: RouteRequest):
    try:
        path = inference_service.route(request.algorithm, request.source, request.target, request.seed)
        if not path:
            raise HTTPException(status_code=404, detail="No active path found")
        return {"algorithm": request.algorithm, "path": path, "policy_version": inference_service.policy.policy_version}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/evaluate", response_model=SimulationMetrics)
def evaluate_routing(request: EvaluateRequest):
    try:
        return inference_service.run_evaluation(request.algorithm, request.num_packets, request.seed)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/compare")
def compare_routing(request: CompareRequest):
    try:
        return inference_service.compare(request.algorithms, request.num_packets, request.seed)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/lab/latest")
def get_latest_results():
    """The current policy's training run and its latest comparison (either may be null)."""
    return inference_service.latest()


@router.get("/dashboard/experiments")
def get_experiments():
    return training_service.get_experiments()


@router.post("/demo/seed")
def seed_demo():
    simulator.build_topology(TopologyType.MESH, 6)
    training_service.reset()
    inference_service.reset()
    training = inference_service.train_policy(400, 17)
    comparison = inference_service.compare([RoutingAlgorithm.DIJKSTRA, RoutingAlgorithm.ECMP, RoutingAlgorithm.RANDOM, RoutingAlgorithm.RL_AGENT], 60, 17)
    return {"training": training, "comparison": comparison}
