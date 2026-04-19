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
DATABASE_URL_SYNC=postgresql://user:password@host:5432/deepsearch
JWT_SECRET=<random 64-char string>
TAVILY_API_KEY=<from tavily.com>
ALLOWED_ORIGINS=https://your-app.railway.app
```

### 2. Local dev

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Deploy to Railway

1. Connect your GitHub repo to Railway
2. Add a Postgres plugin → copy the connection string to `DATABASE_URL`
3. Set env vars in Railway dashboard (JWT_SECRET, TAVILY_API_KEY, ALLOWED_ORIGINS)
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
