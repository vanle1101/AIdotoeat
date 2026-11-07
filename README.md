# AUTOProfit AI

Local source repository for the AUTOProfit dashboard, FastAPI service, and standalone web apps. Production deployment status is not verified by this repository. Automated traffic generation, ad view/click farming, and YouTube watch-to-earn flows are disabled.

## Run locally

Use Python 3.12 or newer. Install the pinned direct runtime and test dependencies:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Keep `.env` private. Set `AUTOPROFIT_ADMIN_API_KEY` to a random value with at least 32 characters. Payment destinations and affiliate settings are blank until configured. The dashboard will show no verified payment or ad data when providers are not connected.

Start the API:

```powershell
Set-Location backend
python -m uvicorn main:app --host 127.0.0.1 --port 8450
```

Serve `frontend/` through a local static server or a reverse proxy that forwards `/api/` to `127.0.0.1:8450`. Administrative API calls require HTTPS and the `X-Admin-Key` header. Do not expose the development server directly to the public internet.

The `run.py` console utilities use the same `.env` file. The global budget and engine kill switches default to on. The local scheduler is disabled by default; set `AUTOPROFIT_ENGINE_WORKER=true` to opt in, and only disable `AUTOPROFIT_ENGINE_KILL_SWITCH` when deliberately processing its local-only queue. External integrations stay dry-run or blocked until exact policy, permission and a one-use owner approval are all present.

The LLM runtime is local-first. Check providers with `python -m core.llm doctor`; benchmark with `python -m core.llm benchmark`. Automatic discovery uses only running Ollama/compatible local servers and installed models, and never downloads weights. Inference stays blocked while `AUTOPROFIT_BUDGET_KILL_SWITCH=true`. Remote OpenAI-compatible calls require a dedicated `AUTOPROFIT_LLM_API_KEY`, HTTPS endpoint, owner-reviewed zero-billing terms, explicit bounded daily quota, and an explicit no-payment-method-exposed setting. The code cannot independently verify billing terms. ChatGPT Plus access is not an API credential. See [PHASE_02_LLM.md](PHASE_02_LLM.md) for provider configuration, usage provenance, tests, and current runtime limitations.

## Data and safety

- Backend SQLite data defaults to `backend/data/company.db`; core task data defaults to `data/company.db`.
- New workflow/task/payment work uses the backend database as canonical. Startup applies additive, versioned engine migrations; it preserves existing tables and data. Before the first update, take a SQLite backup of the backend DB. The core DB remains a read-only legacy source unless the explicit importer in [PHASE_01_ENGINE.md](PHASE_01_ENGINE.md) is run with a pre-existing backup directory.
- Preserve both SQLite files and their `-wal`/`-shm` sidecars before a production migration. Take a consistent SQLite backup with the SQLite backup API or `VACUUM INTO`, validate the copied schema and row counts, and retain the prior deployed release for rollback.
- `frontend/autosurf.html` and `frontend/youtube-booster.html` are inert information pages.
- Public payment reports remain pending until an owner verifies the corresponding statement or on-chain receipt. Public routes cannot mark a payment as paid.
- No actual production health, revenue, visitor, ad-network, or deployment claims are made by this source tree.

See [PHASE_01_ENGINE.md](PHASE_01_ENGINE.md) for the schema ownership map, endpoint inventory, backup/rollback commands, worker behavior, and reproducible test run.
