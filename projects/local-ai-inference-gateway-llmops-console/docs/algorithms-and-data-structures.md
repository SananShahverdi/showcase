# Algorithms and data structures

| Algorithm | Where | Notes |
|---|---|---|
| Provider selection | `routing_policy.select_provider` | Filter (active, capability, privacy) then sort by `(priority, cost_per_1k_tokens)`. |
| Safe fallback | `GatewayService._execute_with_fallback` | Removes a failed provider and reselects with the same filters, so a high-privacy request never falls back to a lower-privacy provider. |
| Fixed-window rate limit | `InMemoryRepository.authenticate` | Count per key within a 60-second window. |
| Token quota | `InMemoryRepository.consume_tokens` | Rejects a request that would exceed the key's quota. |
| PII redaction | `GatewayService.redact` | Regular expressions for e-mail addresses and phone-like digit runs. |
| Strict template rendering | `prompt_registry.compile_prompt` | Every declared variable of the active version must be supplied. |
| Running mean latency | `InMemoryRepository.save_log` | Incremental mean over logical requests. |

## Data structures

| Structure | Purpose |
|---|---|
| `ProviderConfig` | Type, base URL, model, priority, privacy level, capabilities, cost, timeout, health; the provider API key is write-only. |
| `GatewayApiKey` | Name, 12-character prefix, HMAC hash, scopes, limits, tokens used. The plaintext is returned once. |
| `PromptTemplate` / `PromptVersion` | Immutable versions with derived variables and an explicit active version. |
| `RequestLog` | One provider attempt; metadata only. |
| `GatewayMetrics` | Logical requests, provider attempts, errors, fallbacks, tokens, cost, mean latency. |
