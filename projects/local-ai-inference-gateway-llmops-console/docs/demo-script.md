# Demo script

1. Open the gateway console. When a provider already exists (hub demo data), the console issues a scoped key for the browser session and sends the sample prompt once: the playground shows the normalized response with the e-mail address redacted, and the route line names the provider and token count.
2. Walk through the metric cards: logical requests vs provider attempts, attempt success rate, latency, tokens, and fallbacks.
3. Edit the prompt and click **Send chat**, then **Create embedding** to show the deterministic vector.
4. Show **Request log**: attempt-level metadata with no prompt text or key.
5. Show **Prompt versions** and explain strict rendering and explicit activation.
6. Click **Seed secure demo** to reset to a clean provider, template, and one-time key.
7. Close with the boundaries: admin endpoints are open locally, and the deterministic provider is a labeled stand-in for Ollama or vLLM.
