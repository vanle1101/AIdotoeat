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

The `run.py` console utilities use the same `.env` file. The global budget kill switch defaults to on; set `AUTOPROFIT_BUDGET_KILL_SWITCH=false` only when intentionally running a registered, local zero-cost action.

## Data and safety

- Backend SQLite data defaults to `backend/data/company.db`; core task data defaults to `data/company.db`.
- Preserve both SQLite files and their `-wal`/`-shm` sidecars before a production migration. Take a consistent SQLite backup with the SQLite backup API or `VACUUM INTO`, validate the copied schema and row counts, and retain the prior deployed release for rollback.
- `frontend/autosurf.html` and `frontend/youtube-booster.html` are inert information pages.
- Public payment reports remain pending until an owner verifies the corresponding statement or on-chain receipt. Public routes cannot mark a payment as paid.
- No actual production health, revenue, visitor, ad-network, or deployment claims are made by this source tree.
