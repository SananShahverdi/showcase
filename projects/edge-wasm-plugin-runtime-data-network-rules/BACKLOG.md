# Product roadmap

## Delivered local product

- [x] Plugin registry with immutable versions, strict base64 decoding, and Wasm header/import/export validation plus Wasmtime module validation.
- [x] Quarantine of invalid artifacts, canary gating, compare-and-set activation, and rollback through activation history.
- [x] Real Wasmtime execution through the `edge-json-v1` ABI with fuel, memory, deadline, and I/O limits and no host or WASI imports.
- [x] Seeded real Wasm example compiled from inspectable WAT, plus labeled trusted Python adapters.
- [x] Execution history, input hashes, runtime provenance, p50/p95/p99 metrics, and labeled benchmarks.
- [x] Console, unit tests (including Wasmtime limits), and end-to-end API coverage.

## Deployment extensions

- [ ] Add durable registry and execution storage (currently in-memory).
- [ ] Add artifact signing and signature verification before canary.
- [ ] Add a small, audited set of capability-scoped host imports if a plugin genuinely needs them.
- [ ] Add authenticated operator roles for upload, activation, and rollback.
