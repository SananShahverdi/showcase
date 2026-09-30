"""Optional first-visit demo data for the mounted projects.

When ``PORTFOLIO_DEMO_DATA=1`` (set by ``npm start``), the hub loads each
project's own demo scenario at startup so visitors do not land on empty
consoles. A project is seeded only when its listing is empty, so existing
work is never replaced. Seeding goes through each project's public API,
exactly as the "Seed demo" buttons in the consoles do.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("hub.demo")
# Per-request client logs would flood the server log at startup.
logging.getLogger("httpx").setLevel(logging.WARNING)
RAG_ADMIN = {"X-User-ID": "demo-admin", "X-User-Role": "admin", "X-User-Teams": "platform", "X-User-Clearance": "restricted"}

# slug: (listing used to decide whether the project is empty, requests that load the demo, headers)
DEMOS: dict[str, tuple[str, list[tuple[str, dict | list | None]], dict]] = {
    "agentic-ba-automation-platform": ("/api/artifacts", [("/api/demo/seed", None)], {}),
    "ai-code-review-test-gatekeeper": ("/api/dashboard/reports", [
        ("/api/reviews/local", {"id": "pr-101", "repo": "acme/checkout", "title": "Add input validation to checkout",
                                "diff_content": "+def total(items):\n+    return sum(item.price for item in items)\n", "reported_coverage_percent": 91}),
        ("/api/reviews/local", {"id": "pr-102", "repo": "acme/checkout", "title": "Quick fix for payment retries",
                                "diff_content": "+import pickle\n+data = pickle.loads(request.body)\n+password = 'hunter2'\n", "reported_coverage_percent": 64}),
    ], {}),
    "ai-security-playground-llm-applications": ("/api/runs", [("/api/assessment", None)], {}),
    "aiops-incident-assistant-human-approval": ("/api/incidents", [
        ("/api/incidents/generate", {"type": "latency_spike", "service_name": "checkout-api"}),
        ("/api/incidents/generate", {"type": "high_error_rate", "service_name": "auth-service"}),
        ("/api/incidents/generate", {"type": "queue_backlog", "service_name": "orders-worker"}),
    ], {}),
    "autonomous-data-quality-observatory": ("/api/sources", [("/api/demo/seed", None)], {}),
    "compliance-aware-rag-knowledge-base": ("/api/admin/documents", [("/api/demo/seed", None)], RAG_ADMIN),
    "edge-wasm-plugin-runtime-data-network-rules": ("/api/plugins", [("/api/demo/seed", None)], {}),
    "internal-developer-portal-golden-paths": ("/api/catalog", [
        ("/api/scaffold", {"template_id": "worker-base", "service_name": "ledger-worker", "owner": "team-payments",
                           "description": "Reconciles settled payments into the ledger"}),
        ("/api/scaffold", {"template_id": "fastapi-base", "service_name": "payments-api", "owner": "team-payments",
                           "description": "Payment intents and refunds API", "parameters": {"port": "8001"}}),
    ], {}),
    "local-ai-inference-gateway-llmops-console": ("/api/admin/templates", [("/api/demo/seed", None)], {}),
    "network-digital-twin-rl-routing-optimizer": ("/api/dashboard/experiments", [("/api/demo/seed", None)], {}),
    "post-quantum-crypto-migration-scanner": ("/api/scans", [("/api/demo/seed", None)], {}),
    "process-mining-workflow-automation-analyzer": ("/api/reports", [("/api/demo/seed", None)], {}),
    "real-time-fraud-risk-stream-analytics": ("/api/alerts", [("/api/demo/seed", None)], {}),
    "self-healing-public-data-intelligence-pipeline": ("/api/runs", [("/api/demo/seed", None)], {}),
    "smart-network-capacity-planner": ("/api/links", [("/api/demo/seed", None)], {}),
    "delivery-desk": ("/api/tasks", [("/api/demo/seed", None)], {}),
    "stockroom-inventory": ("/api/items", [("/api/demo/seed", None)], {}),
}


async def gateway_traffic(client: httpx.AsyncClient, seeded: dict) -> None:
    """Send a little real traffic through the offline provider so logs and metrics are not empty."""
    headers = {"Authorization": f"Bearer {seeded['api_key']['key']}"}
    for content, privacy in (("Summarize the quarterly incident review for the platform team.", False),
                             ("Draft a reply to alice@example.com about the delayed invoice.", True),
                             ("List three risks in migrating the billing service.", False)):
        response = await client.post("/v1/chat/completions", headers=headers, json={
            "messages": [{"role": "user", "content": content}], "requires_high_privacy": privacy, "redact_pii": privacy})
        response.raise_for_status()
    (await client.post("/v1/embeddings", headers=headers, json={"input": ["incident review", "billing migration"]})).raise_for_status()


# slug: called with the client and the JSON returned by the last demo request.
FOLLOW_UPS = {"local-ai-inference-gateway-llmops-console": gateway_traffic}


def is_empty(payload) -> bool:
    """True when a listing has no records: an empty list, or a mapping whose lists are all empty."""
    if isinstance(payload, list):
        return not payload
    if isinstance(payload, dict):
        lists = [value for value in payload.values() if isinstance(value, list)]
        return bool(lists) and all(not value for value in lists)
    return False


async def seed_demos(mounted: dict) -> dict[str, str]:
    """Seed every empty project; returns a per-project outcome for logging and tests."""
    outcomes = {}
    for slug, (listing, requests, headers) in DEMOS.items():
        app = mounted.get(slug)
        if app is None:
            continue
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1", headers=headers, timeout=120) as client:
            try:
                current = await client.get(listing)
                if current.status_code != 200 or not is_empty(current.json()):
                    outcomes[slug] = "kept existing data"
                    continue
                for path, body in requests:
                    response = await client.post(path, json=body) if body is not None else await client.post(path)
                    response.raise_for_status()
                if slug in FOLLOW_UPS:
                    await FOLLOW_UPS[slug](client, response.json())
                outcomes[slug] = "seeded"
            except Exception as exc:  # noqa: BLE001 - one project's demo must not stop the hub
                outcomes[slug] = f"skipped ({type(exc).__name__})"
                logger.warning("Demo data for %s was not loaded: %s", slug, exc)
    logger.info("Demo data: %s", ", ".join(f"{slug}={outcome}" for slug, outcome in outcomes.items()))
    return outcomes
