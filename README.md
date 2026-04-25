# IntelliSys

System-level developer intelligence: scan code, track APIs, monitor calls, diff snapshots, and surface insights (including optional OpenAI).

## Prerequisites

- Python 3.11+
- Node 20+ (for the Angular UI)
- Docker (optional) for PostgreSQL, or a managed Postgres

## Database

1. Copy [.env.example](.env.example) to `backend/.env` and set `DATABASE_URL` if needed.
2. Start PostgreSQL, for example: `docker compose up -d db` from the repo root.
3. From `backend/`, run: `alembic upgrade head` (includes GitHub project columns in migration `0002`).

**If `alembic upgrade` fails with `Connection refused` on port 5432:** PostgreSQL is not running or nothing is listening on that host/port. Start the database first, e.g. from the repo root `docker compose up -d db`, or start your local Postgres service. If another app already uses `5432`, set `POSTGRES_PORT` in `.env` / `docker-compose` and the same port in `DATABASE_URL` in `backend/.env`. Copy `.env.example` to `backend/.env` and adjust `DATABASE_URL` if needed.

## Backend

**If `pip install -r requirements.txt` fails with “Could not open requirements file”:** run it from the `backend/` folder, or from the repo root (there is a root `requirements.txt` that includes `backend/requirements.txt`).

```text
cd backend
python -m pip install -r requirements.txt
# create backend/.env with DATABASE_URL, CORS_ORIGINS, optional OPENAI_API_KEY
set PYTHONPATH=.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: `http://127.0.0.1:8000/docs`
- Health: `GET /health`
- n8n (optional): `docker compose --profile n8n up -d` or use [n8n Cloud](https://n8n.io). Your workflow must call a **publicly reachable** API URL (deploy the API or use a **tunnel** such as ngrok/Cloudflare Tunnel). Do not use a changing tunnel URL for production—use a reserved hostname when possible.
- **n8n + localhost / “restricted IP (SSRF)”** — n8n blocks `127.0.0.1` and private ranges on outbound HTTP for safety. The compose profile sets `N8N_SSRF_ALLOWED_IP_RANGES` and `N8N_SSRF_ALLOWED_HOSTNAMES` so **self-hosted** n8n can call IntelliSys. If the API runs on your **host** and n8n runs **in Docker**, use the URL **`http://host.docker.internal:8000`** in the HTTP Request node, not `http://127.0.0.1:8000` (the container’s loopback is not your host). **n8n Cloud** cannot see your PC’s `127.0.0.1`; you must use a **tunnel** or public API URL. For `npx n8n` on the same machine, set the same `N8N_SSRF_*` variables in the environment (see [n8n SSRF](https://docs.n8n.io/hosting/configuration/environment-variables/ssrf-protection/)).
- **Automation webhook** — `POST /automation/n8n-webhook` with header `X-IntelliSys-Secret` equal to `AUTOMATION_WEBHOOK_SECRET` in `backend/.env`. Store the secret in n8n **Credentials**, not in the workflow JSON.
  - **`{"action": "ping"}`** — smoke test; returns `pong: true` without running a scan.
  - **`{"action": "daily_scan", "project_id": <n>, "with_snapshot": true}`** — Git sync (if the project has a GitHub URL), full file scan, **recompute** dead/slow issues, and an optional **snapshot** (same as manual “Sync & full scan”).
- **GitHub** — set `GITHUB_TOKEN` in `backend/.env` for private repositories. Clones are stored under `WORKSPACE_BASE` or `backend/data/workspaces` by default. Install **git** on the API host.

## Deploy (Render)

**“Port scan timeout / no open ports”** — Render probes the process bound to the **`PORT`** env var. If nothing is listening in time, you get this error. **Troubleshoot in order:**

1. **Start command (required)** — either:
   - `sh start-render.sh` (uses [`backend/start-render.sh`](backend/start-render.sh), sets `PYTHONPATH` and `python -m uvicorn` on `$PORT`), **or**
   - `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
   **Wrong:** `--port 8000` only, or `127.0.0.1` as host, or a command that **exits** before the server starts (see logs).
2. **Root directory:** `backend` (so `app.main:app` imports correctly).
3. **Runtime:** **Python** (not Node; npm-only builds never open your API port).
4. **Build:** `pip install -r requirements.txt` (With root `backend`, that file is `backend/requirements.txt`.)
5. **Read deploy logs** — if you see `ModuleNotFoundError` / exit code 1, the web process never started; fix the error first.
6. **Environment:** set **`DATABASE_URL`** to your Render Postgres (link DB or paste URL). A crash on the **first** request is less common than a bad **start**; still verify vars after the service is **live**.

**Import / `ModuleNotFoundError: No module named 'app'`** — your **Root directory** must be **`backend`** (this repo has `app` under `backend/app/`, not at the repo root). The log path may show `.../project/src/...`; that is Render’s build tree, not a folder you name `src`. After pull, use start command `sh start-render.sh` (it `cd`s into `backend/`).

**Python 3.14 on Render** — new services default to **3.14**. This project is tested on **3.11**. The repo includes [`.python-version`](.python-version) and [`render.yaml`](render.yaml) sets **`PYTHON_VERSION=3.11.11`**. In the dashboard, add the same **Environment** variable if you don’t use the Blueprint.

**Health check path:** `/health` in the service settings (optional; matches [`health`](backend/app/routes/health.py)).

Set **`AUTOMATION_WEBHOOK_SECRET`**, **`CORS_ORIGINS`** (your deployed UI origin, comma-separated if many), and optional keys from [`.env.example`](.env.example) in **Environment**. See [`render.yaml`](render.yaml).

## Frontend

```text
cd frontend
npm install
ng serve --port 4200
```

The dev server expects the API at `http://localhost:8000` (see `src/environments/environment.ts`).

## First project

1. Open the **Dashboard** and register a project with a **local path** and/or a **GitHub** repository URL. For GitHub-only projects, the server clones into the workspace directory on first **Run scan** or **Sync & full scan (Git)**.
2. Run **Run scan** (or **Sync & full scan (Git)** for remote repos) — the pipeline can **recompute** issues and create a **snapshot** automatically for GitHub-linked projects. Open **APIs** to see routes extracted from Python files.
3. Call monitored endpoints with header `X-Project-Id: <id>` to record `api_calls`, or `POST /monitor/ingest` with `api_id` fields.
4. Use **Issues** and **Alerts** for report-style lists; use **Recompute issues** or the automated n8n flow to refresh dead/slow detection. **AI insight** and **Chat** work when `OPENAI_API_KEY` is set.
