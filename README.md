# DeepSearch API

Multi-agent deep research pipeline — Tavily web search + LLM synthesis via OpenRouter/Z.ai/MiniMax.

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/crypto2retire/deepsearch.git
cd deepsearch
cp .env.example .env
```

Fill in `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/deepsearch
JWT_SECRET=<generate with: python -c "import secrets; print(secrets.token_urlsafe(64))">
TAVILY_API_KEY=<from tavily.com>
ALLOWED_ORIGINS=https://your-app.railway.app
```

Note: `DATABASE_URL_SYNC` is auto-derived from `DATABASE_URL` (the `+asyncpg` prefix is stripped automatically).

### 2. Local dev

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Deploy to Railway

1. Connect your GitHub repo to Railway
2. Add a **Postgres plugin** to the project
3. In your app service's **Variables** tab:
   - Click **Add Reference Variable** → select your Postgres plugin → choose `DATABASE_URL`
   - (Optional) Add `DATABASE_URL_SYNC` — same value but strip the `+asyncpg` prefix
   - Add `JWT_SECRET` (generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`)
   - Add `TAVILY_API_KEY` (from tavily.com)
   - Add `ALLOWED_ORIGINS` = your Railway app URL (e.g. `https://deepsearch.up.railway.app`)
4. Railway auto-deploys on push to `main`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register with email + password |
| POST | `/auth/login` | Login → returns JWT |
| GET | `/auth/me` | Current user info |
| POST | `/settings/llm` | Save LLM preferences + API key |
| GET | `/settings/llm` | Get current LLM preferences |
| POST | `/research` | Start a research job |
| GET | `/research/{id}/stream` | SSE stream of research progress |
| GET | `/research/{id}` | Poll for completed result |
| GET | `/research` | Research history |
| GET | `/health` | Health check |

## Architecture

```
Query → Planner (8B) → Researcher #1 + #2 (70B, parallel) → Synthesizer (70B) → Answer
                    ↓                         ↓
              Tavily search              Tavily search
```

## Required Secrets (Railway)

- `RAILWAY_TOKEN` — from Railway account settings
- `RAILWAY_PROJECT_ID` — from Railway project URL
