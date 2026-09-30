#!/bin/bash
set -e

PROJECTS=(
  "compliance-aware-rag-knowledge-base"
  "self-healing-public-data-intelligence-pipeline"
  "agentic-ba-automation-platform"
  "local-ai-inference-gateway-llmops-console"
  "network-digital-twin-rl-routing-optimizer"
  "aiops-incident-assistant-human-approval"
  "ai-code-review-test-gatekeeper"
  "internal-developer-portal-golden-paths"
  "real-time-fraud-risk-stream-analytics"
  "ai-security-playground-llm-applications"
  "post-quantum-crypto-migration-scanner"
  "process-mining-workflow-automation-analyzer"
  "edge-wasm-plugin-runtime-data-network-rules"
  "smart-network-capacity-planner"
  "autonomous-data-quality-observatory"
  "delivery-desk"
  "stockroom-inventory"
  "quant-research-lab"
  "multitask-ppo-lab"
)

TOTAL=${#PROJECTS[@]}
PASSED=0
FAILED=0
FAILED_LIST=()

echo "========================================"
echo "Running Global Verification Suite"
echo "========================================"

for proj in "${PROJECTS[@]}"; do
  echo "----------------------------------------"
  echo "Testing Project: $proj"
  
  if [ -d "$proj" ]; then
    cd "$proj"
    
    # We use pip to install dev reqs quietly if possible, then run pytest
    export PYTHONPATH=src
    if pytest tests/ -q; then
      echo "✅ PASSED: $proj"
      PASSED=$((PASSED+1))
    else
      echo "❌ FAILED: $proj"
      FAILED=$((FAILED+1))
      FAILED_LIST+=("$proj")
    fi
    
    cd ..
  else
    echo "⚠️ DIRECTORY NOT FOUND: $proj"
    FAILED=$((FAILED+1))
    FAILED_LIST+=("$proj")
  fi
done

echo "========================================"
echo "Verification Summary"
echo "========================================"
echo "Total Projects: $TOTAL"
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ $FAILED -gt 0 ]; then
  echo "Failed Projects:"
  for f in "${FAILED_LIST[@]}"; do
    echo "  - $f"
  done
  exit 1
fi

echo "All projects passed successfully! 🎉"
exit 0
