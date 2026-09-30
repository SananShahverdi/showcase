#!/usr/bin/env bash
set -euo pipefail

PROJECTS=(
  agentic-ba-automation-platform
  self-healing-public-data-intelligence-pipeline
  network-digital-twin-rl-routing-optimizer
  local-ai-inference-gateway-llmops-console
  aiops-incident-assistant-human-approval
  ai-code-review-test-gatekeeper
  internal-developer-portal-golden-paths
  real-time-fraud-risk-stream-analytics
  ai-security-playground-llm-applications
  post-quantum-crypto-migration-scanner
  process-mining-workflow-automation-analyzer
  edge-wasm-plugin-runtime-data-network-rules
  smart-network-capacity-planner
  autonomous-data-quality-observatory
  compliance-aware-rag-knowledge-base
)

for project in "${PROJECTS[@]}"; do
  echo "Checking frontend: ${project}"
  (
    cd "${project}/frontend"
    if [[ ! -d node_modules ]]; then
      npm install
    fi
    npm run lint
    npm run build
  )
done

echo "All 15 frontend lint and production-build checks passed."

