# Phase 02 — Local-first LLM runtime

## Repository audit and integration

The previous role registry described 50 logical roles but did not make model calls. The market scout returned static niche templates, and the proposal crafter asserted that work was already ready. Phase 02 replaces those claims with clearly labeled unverified seed ideas and a `DEGRADED_MODE` proposal skeleton. The orchestrator now exposes source-grounded niche classification, evidence extraction, and proposal personalization through `core.llm.LLMGateway`. The venture action returns `BLOCKED` when source material or a health-checked provider is missing, and `ANALYSIS_ONLY` after classification; it no longer manufactures a market, price, deliverable, revenue, or payment QR from static examples.

## Providers and safety

`ModelRouter` supports:

- Ollama at the configured loopback endpoint. It only selects a model already returned by `/api/tags`; automatic selection chooses the largest installed model no larger than half of currently available system RAM. It never invokes `ollama pull`.
- A running loopback OpenAI-compatible server such as llama.cpp at a configured endpoint or common local ports. The model must be discoverable from `/v1/models` unless explicitly configured.
- A remote OpenAI-compatible provider only when the dedicated key, HTTPS endpoint/model, owner-reviewed HTTPS billing terms, daily quota from 1–1000, and explicit `AUTOPROFIT_LLM_PAYMENT_METHOD_EXPOSED=false` are all present. This configuration is an owner attestation, not independent verification by the application. No billing or card-check request is made. Generic `OPENAI_API_KEY` is ignored, and ChatGPT Plus is not treated as API access.
- An explicitly selected deterministic template provider. Its outputs carry `DEGRADED_MODE`; it cannot produce factual research and does not claim model reasoning.

`python -m core.llm doctor` reports provider readiness, hardware detectable on the current host, budget-switch state, and safe reason codes without exposing credentials. The `benchmark` command runs niche classification, evidence extraction, and proposal personalization against the selected model. A template provider cannot count as a real-model benchmark. Structured tasks use Pydantic JSON Schema validation, input and output budgets, bounded retries, timeouts, exact evidence-ID checks, and explicit instructions that scraped text is untrusted data. Optional tool calls require a non-executing capability probe; returned calls are schema-checked and never executed by the gateway.

Usage counts are stored in the canonical `backend/data/company.db` under schema migration 006. Rows record provider/model, reported token counts or `NULL`, latency, status, failure code, trace ID, and a confidence estimate labeled `model_estimate_unvalidated`. Prompt bodies and API keys are not stored. A 24-hour bounded cache stores validated output for niche/evidence tasks (not customer-specific proposals); it is local and should be protected like other business data.

Inference observes the existing default-on `AUTOPROFIT_BUDGET_KILL_SWITCH`. Disable it only when deliberately enabling local inference. Remote inference also consumes its bounded request quota; each attempted provider request is reserved before it is sent. Remote `/models` health checks and tool-capability probes count toward the same daily quota, so set it high enough for those checks plus the planned inference requests.

## Runtime snapshot

The Phase 02 start-of-workstation audit recorded Windows 11, Python 3.12, 12 logical CPUs, 15.7 GiB total RAM (about 2.0 GiB available at the time of the doctor check), and an NVIDIA RTX 2050 with 4 GiB VRAM. The audit found no Ollama or llama.cpp runtime, no active local inference server, and no installed model suitable for inference. The generic `OPENAI_API_KEY` variable was present but its value was neither read nor used; the dedicated AUTOProfit key was absent. Run `python -m core.llm doctor` for a fresh host report. Installed-model availability and hardware remain environment-specific; these facts are not deployment assertions.

No real-model benchmark is claimed until a real provider returns all three benchmark outputs. The in-process fake LLM server validates protocol handling only and is not an AI quality benchmark.

## Verification

Run the tests with the existing pinned environment:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest tests.test_llm_runtime -v
python -B -m unittest tests.test_engine tests.test_phase00_safety tests.test_phase01_engine -v
python -m core.llm doctor
python -m core.llm benchmark
```

The fake-server tests cover structured success and provenance, local-cache hits, 429 retry, outage, malformed JSON, truncated response, scraped prompt injection isolation, undeclared/incompatible tools, and remote configuration gating. Benchmark output must say `UNAVAILABLE` when no real provider is ready.
