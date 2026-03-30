# CSS Prep AI

Multi-LLM chatbot for Pakistan CSS exam preparation.
Powered by GPT-4o-mini, Claude, and Gemini with JWT auth and streaming.

## Tech Stack

| Layer     | Technology                              |
|-----------|-----------------------------------------|
| Backend   | FastAPI, Pydantic, SQLAlchemy async     |
| Database  | PostgreSQL 16                           |
| Frontend  | React 18, Vite, Tailwind CSS            |
| Auth      | JWT (python-jose)                       |
| Proxy     | Nginx (with SSE proxy)                  |
| Infra     | Docker, Docker Compose                  |
| Observability | MLflow, Structlog                   |

## Project Structure

```text
css-prep-ai/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── feedback_router.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── gpt.py
│   │   │   ├── claude.py
│   │   │   └── gemini.py
│   │   ├── middleware/
│   │   │   └── logging.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   ├── mlops/
│   │   │   ├── mlflow_tracker.py
│   │   │   ├── prompt_manager.py
│   │   │   └── quality_monitor.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   ├── config.py
│   │   └── main.py
│   ├── alembic/
│   │   └── versions/
│   │       └── 001_create_users_table.py
│   ├── prompts/
│   ├── tests/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── mlflow/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.docker.example
├── Makefile
├── .gitignore
└── README.md
```

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Docker Compose v2 (comes with Docker Desktop)
- API keys for OpenAI, Anthropic, and Google Gemini

## Quick Start with Docker (Recommended)

### Step 1 — Clone and configure

```bash
git clone https://github.com/Khan-Feroz211/EliteCSS-AI.git
cd EliteCSS-AI
cp .env.docker.example .env.docker
# Edit .env.docker with your real API keys, a strong POSTGRES_PASSWORD,
# and a long JWT_SECRET (minimum 32 characters)
```

### Step 2 — Start everything

```bash
make up
# or: docker-compose up -d
# First run takes 2-3 minutes to build images
```

### Step 3 — Verify all services are healthy

```bash
docker-compose ps
# All three should show status: healthy or running

curl http://localhost:8000/health
# → {"status":"ok","uptime_seconds":N,"models_available":[...]}

curl http://localhost/api/v1/health
# → same response through nginx proxy (confirms proxy is working)
```

### Step 4 — Open the app

Open [http://localhost](http://localhost) in your browser, click **Register**, and start chatting.

## Manual Setup (Without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in your keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: http://localhost:5173

## Available Make Commands

| Command              | Description                                    |
|----------------------|------------------------------------------------|
| `make up`            | Start all services (detached)                  |
| `make down`          | Stop all services                              |
| `make build`         | Rebuild all Docker images (no cache)           |
| `make logs`          | Follow logs from all services                  |
| `make logs-backend`  | Follow backend logs only                       |
| `make migrate`       | Run database migrations inside container       |
| `make shell-backend` | Open a shell inside the backend container      |
| `make shell-db`      | Open psql inside the postgres container        |
| `make reset`         | Stop, remove volumes, and restart fresh        |
| `make prod-up`       | Start production compose stack                 |
| `make prod-down`     | Stop production compose stack                  |
| `make prod-build`    | Rebuild production images (no cache)           |

## Environment Variables

| Variable                   | Description                               | Example                          |
|----------------------------|-------------------------------------------|----------------------------------|
| `OPENAI_API_KEY`           | OpenAI API key                            | `sk-proj-...`                    |
| `CLAUDE_API_KEY`           | Anthropic API key                         | `sk-ant-...`                     |
| `GEMINI_API_KEY`           | Google Gemini API key                     | `AIza...`                        |
| `POSTGRES_USER`            | PostgreSQL username                       | `postgres`                       |
| `POSTGRES_PASSWORD`        | PostgreSQL password                       | `strongpassword`                 |
| `POSTGRES_DB`              | PostgreSQL database name                  | `css_prep_ai`                    |
| `JWT_SECRET`               | Secret for signing JWT tokens (≥32 chars) | `$(openssl rand -hex 32)` |
| `APP_ENV`                  | Application environment                   | `development` / `production`     |
| `LOG_LEVEL`                | Logging level                             | `INFO`                           |

## API Endpoints

| Method | Path                       | Auth Required | Description              |
|--------|----------------------------|---------------|--------------------------|
| GET    | `/health`                  | No            | Liveness check           |
| POST   | `/api/v1/auth/register`    | No            | Create account           |
| POST   | `/api/v1/auth/login`       | No            | Get JWT token            |
| POST   | `/api/v1/chat`             | Yes           | Single response          |
| POST   | `/api/v1/chat/stream`      | Yes           | SSE streaming response   |

## Roadmap

- **Day 5**: MLflow observability
- **Day 6**: CI/CD pipeline
- **Day 7**: Stripe billing
- **Day 8**: Kubernetes
- **Day 9**: Production deployment
