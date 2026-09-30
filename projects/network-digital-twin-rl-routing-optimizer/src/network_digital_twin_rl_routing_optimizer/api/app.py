from fastapi import FastAPI
from network_digital_twin_rl_routing_optimizer.api.routes import router

app = FastAPI(title="Network Digital Twin RL Routing Optimizer", version="1.0.0")
app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from network_digital_twin_rl_routing_optimizer.adapters.database import install  # noqa: E402
from network_digital_twin_rl_routing_optimizer.api.persistence import build_persistence  # noqa: E402
from network_digital_twin_rl_routing_optimizer.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
