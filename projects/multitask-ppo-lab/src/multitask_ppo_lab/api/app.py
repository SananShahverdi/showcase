"""FastAPI application for the trained-agent console."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from multitask_ppo_lab.services.lab_service import LabService, NotReady

FRONTEND = Path(__file__).resolve().parents[3] / "frontend"


class EpisodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: Literal["navigation", "key_door"]
    policy: Literal["ppo", "ppo_greedy", "random", "oracle"] = "ppo"
    seed: int = Field(default=1, ge=0, le=1_000_000)


def create_app(service: LabService | None = None) -> FastAPI:
    app = FastAPI(title="Multi-Task PPO Lab", version="1.0.0")
    lab = service or LabService()

    @app.get("/health")
    def health():
        return {"status": "ok", "policy_loaded": lab.ready}

    @app.get("/api/summary")
    def summary():
        try:
            return lab.summary()
        except NotReady as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/episodes")
    def episode(payload: EpisodeRequest):
        try:
            return lab.episode(payload.task, payload.policy, payload.seed)
        except NotReady as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    if FRONTEND.exists():
        app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
    return app


app = create_app()
