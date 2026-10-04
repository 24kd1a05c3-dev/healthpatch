# HealthPatch

Research monitoring prototype: React/TypeScript, FastAPI and MongoDB. **Not a diagnostic device or emergency dispatch service. Not yet approved for production patient use.** See [implementation audit](docs/IMPLEMENTATION.md) for completed work, verification and release blockers.

Production hardening and the Docker/Twilio rollout procedure are documented in [production deployment](docs/PRODUCTION.md). Infrastructure and real provider delivery still require staging verification.

## Run locally in VS Code

Open the entire project, not only the frontend:

```powershell
code D:\Documents\healthpatch
```

Frontend code is in `src`; backend code is in `backend/app`. MongoDB must be running at `mongodb://localhost:27017` (or configure `MONGODB_URI`). Use Node.js 22.12+ and Python 3.11+.

The project-local Python environment is installed in this workspace. For a fresh checkout, run this one-time setup in PowerShell:

```powershell
Set-Location D:\Documents\healthpatch
npm ci
py -3 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Copy-Item backend\.env.example backend\.env
```

Do not overwrite an existing `.env`. Replace `JWT_SECRET_KEY` in `backend/.env` with a private randomly generated secret. SMTP settings are commented out by default; password-reset email reports unavailable until configured.

If the Windows Python launcher (`py`) is unavailable on this machine, create the environment with the bundled runtime instead:

```powershell
& 'C:\Users\anirudh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv backend\.venv
```

Terminal 1, backend:

```powershell
Set-Location D:\Documents\healthpatch\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 2, frontend:

```powershell
Set-Location D:\Documents\healthpatch
npm run dev -- --host 127.0.0.1 --port 5173
```

Open [HealthPatch](http://127.0.0.1:5173/) and [API documentation](http://127.0.0.1:8000/docs). Keep the hostname consistent: do not alternate `localhost` and `127.0.0.1` within a session. Stop a foreground server with Ctrl+C before starting another on its port.

## Use

1. Register a patient. The phone selector defaults to India +91; other countries, valid landlines, additional numbers and an emergency contact are supported. Saved phone links open the operating system dialer. Settings now supports Twilio verification and opt-in SMS/voice when an operator configures the provider; it is disabled locally.
2. Open **Signal Lab**, select installed `bidmc_01`, and start replay. Inspect five waveform channels and four numerics; pause, change speed, seek, toggle channels or freeze plots. Dataset replay is historical real data, not a live patient feed.
3. Open **Digital Twin** or **Dashboard** to inspect persisted measurements, baseline statistics, trends and alerts. Missing measurements remain missing.
4. Stop replay before starting **Research Simulator**. Its numerical scenarios are visibly marked SIMULATED DATA. Allow at least 60 samples for baseline availability; collect a resting baseline before changing scenario to exercise deviation detection.
5. Acknowledge a recorded observation and export CSV. These actions use the backend and are audited.

Only BIDMC record 01 is installed locally. See [dataset instructions and attribution](docs/DATASETS.md) to install additional licensed records. Do not run legacy `backend/seed.py` or `backend/generator.py` against patient data; they are not part of the validated flow.

## Verify

Frontend:

```powershell
Set-Location D:\Documents\healthpatch
npm run typecheck
npm test
npm run build
```

Backend (MongoDB required by API tests):

```powershell
Set-Location D:\Documents\healthpatch\backend
.\.venv\Scripts\python.exe -m pytest tests -q
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe tests\run_live_checks.py
```

For the live checks, the API must also be running on port 8000.

The live-check script creates an isolated QA patient and cleans up its own records. Do not point it at a production database. There is no configured lint gate yet; build/type checks are not substitutes for lint.

## Deployment boundary

`npm run build` creates static assets in `dist`; Vite dev/preview are not production servers. Production needs HTTPS, an authenticated/private database, backups with restore testing, secrets management, a same-site frontend/API deployment with explicit CORS, verified SMTP and the security/reliability work listed in the audit. Use one API worker for now: replay, simulator and WebSocket registries are process-local. `/health` is liveness and `/ready` checks MongoDB.

Startup creates additive indexes; it is not a migration/backfill system. Existing access tokens without a session ID are invalidated and users must sign in again. No Docker deployment, clinical validation or high-concurrency certification is claimed.

## Troubleshooting

- Focus lost while editing: reload the browser once after development updates. The form fields now have stable React identities and automated regression tests.
- API unavailable: check `/ready`, MongoDB and the backend terminal. Do not replace failed responses with demo data.
- No recording installed: inspect `backend/datasets/bidmc_csv`, add matching Signals/Numerics files and restart the API.
- Empty dashboard: start a source; an empty workspace is intentional before telemetry exists.
- Session expired: sign in again. Multi-tab refresh coordination still needs hardening before production.
- Phone link does not open a call: a telephone handler must be installed on that computer; the application does not itself place calls.

## Public Vercel demonstration
Vercel builds with VITE_PUBLIC_DEMO=true. This loads the isolated DemoApp rather than the authenticated backend application. All readings are generated in the browser; no backend credentials, accounts or patient data are used. Use the normal local development command for the full research application.

