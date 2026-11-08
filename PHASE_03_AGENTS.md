# Phase 03 — Task-scoped agents

Phase 03 keeps the 50 IDs in `core/roles.py` as logical business roles. It does
not create 50 model instances. Roles map to a small set of reusable local
handlers in `core/agent_runtime.py`; four roles currently report
`NOT_IMPLEMENTED`: `DEV_CHROME_EXT_BUILDER`, `DEV_SCRAPER_SPECIALIST`,
`DEV_TELEGRAM_BOT_CRAFTER`, and `OPS_VIETQR_ARCHITECT`.

`READY` means the role has a bounded handler. Most handlers use deterministic
`LOCAL_RULES`; that label is not a claim of LLM inference. When a task requires
LLM reasoning, it uses Phase 02's installed local Ollama/llama.cpp runtime,
respects the registry token cap and the run budget, and blocks if no real local
provider is ready. Template mode is not selected as an agent. Inference
concurrency is capped at one. Hardware readiness is reported by the runtime
profile and remains unverified for the production VPS until checked there.

The local `doctor` check during this phase reported Windows 11, Python 3.12.10,
12 logical CPUs, 16 GiB system RAM with about 1.6 GiB available, and an RTX
2050 with 4 GiB VRAM. Ollama was unreachable, no fitting llama.cpp model was
installed, remote calls were disabled, and the budget kill switch was on. This
machine therefore did not run model inference for the E2E workflow.

## Workflow and safety

The default public-problem pipeline persists sequential tasks, events, source
citations, run state, and draft artifacts in the canonical backend SQLite
ledger (schema migration 007). Handoffs are limited to each handler's explicit
predecessors. The run is bounded by 16 steps, 120 seconds, one depth level,
10,000 context characters, and the registry's model-output budgets. Artifacts
are local drafts with a SHA-256 digest and source IDs. Source-cited memory has
a maximum 365-day TTL and can be explicitly deleted; expired memory is removed
when read.

External contact, publication, payment, purchase, or fulfillment is never
performed by these handlers. A requested effect persists a `WAITING_APPROVAL`
task and owner handoff; approving it only permits a retry. Since there is no
registered executor for that external action, the retried task blocks without
performing it. Owner controls use the existing HTTPS + admin-key guard.

LangGraph and Deep Agents were not added: the current workflow is a bounded
linear queue with SQLite checkpoints and explicit permission gates, so another
runtime would add state machinery without improving the local executor.

## API

- `GET /api/agents/registry` — all logical roles, handlers, readiness, skills,
  tools, budgets, side effects, metrics, and output schemas.
- `GET /api/agents/runtime` — actual concurrency cap, hardware probe, and
  configured limits.
- `GET /api/agents/status` — each role's latest persisted task state.
- `POST /api/agents/workflows` — validate and enqueue a public-source workflow.
- `GET /api/agents/workflows` and `/api/agents/workflows/{run_id}` — run
  history and task handoffs.
- `GET /api/agents/artifacts/{artifact_id}` — retrieve an owner-only draft.
- `GET /api/agents/memory?namespace=...` and
  `DELETE /api/agents/memory/{memory_id}` — source-cited memory and deletion.
- `GET /api/engine/events` — authenticated SSE from persisted task events.

Agent detail is included in `/api/dashboard` only for an authenticated owner.
The public active-agent aggregate now counts only canonical `agent.execute`
tasks with an unexpired lease and a recorded task event.

## Skills and verification

Skills are small versioned Python modules in `core/skills/`. The five-agent
integration test uses a saved public MIT-licensed GitHub issue snapshot in
`tests/fixtures/phase03_public_problem.json`. It builds and contract-tests a
local duplicate-pairs CSV exporter draft. The snapshot's request to comment or
claim the issue is untrusted source text: no comment, claim, contact, PR, or
publication is made. A read-only GitHub REST check on 2026-11-08 confirmed the
issue was open, the repository SPDX license was MIT, and the current body
matched the fixture after whitespace normalization. Other API-submitted
snapshots are owner-provided; the runtime checks canonical URL shape and an
allowlisted declared license, but does not fetch GitHub metadata for every run.

Run the Phase 03 and model-budget checks:

```powershell
python -m unittest tests.test_phase03_agents tests.test_llm_runtime -v
```

Run all repository tests:

```powershell
python -m unittest discover -s tests -v
```

The tests cover all 50 role mappings, one five-agent cross-department run from
the public issue to a persisted QA-passing artifact, unavailable required LLM,
contradictory evidence, unsafe side-effect approval/retry, malformed handler
output, memory TTL/deletion, authenticated API routes, dashboard lease/event
status, and LLM output-token caps.
