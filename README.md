# CSS Prep AI

CSS Prep AI is a production-oriented multi-LLM chatbot platform for Pakistan CSS exam preparation.
It routes user prompts to GPT-4o-mini, Claude, or Gemini through a FastAPI backend and a React + Vite frontend.

## Features

- Multi-provider routing: OpenAI, Anthropic, Google Gemini
- Multi-turn chat with streaming responses (SSE)
- Structured logging with request metadata
- Rate limiting and request validation
- Prompt management with A/B testing
- MLflow observability for latency, tokens, and response quality
- Feedback loop endpoint backed by async SQLite
- Containerized local and production setups
- CI/CD pipeline with lint, test, image build, and deploy placeholder

## Tech Stack

- Backend: FastAPI, Pydantic, SlowAPI, Structlog, SQLAlchemy async, MLflow
- Frontend: React 18, Vite, Tailwind CSS
- Infra: Docker, Docker Compose, Nginx, GitHub Actions

## Project Structure

```text
css-prep-ai/
├── backend/
│   ├── app/
│   │   ├── routers/
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
│   ├── prompts/
│   │   ├── css_prep_v1.yaml
│   │   └── css_prep_v2.yaml
│   ├── tests/
│   │   └── test_chat.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageInput.jsx
│   │   │   ├── ModelSelector.jsx
│   │   │   ├── FeedbackButtons.jsx
│   │   │   └── StreamingMessage.jsx
│   │   ├── hooks/
│   │   │   └── useLocalStorage.js
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
├── .env.example
├── .gitignore
└── README.md
```

## Local Development

### 1) Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: http://localhost:5173

## Run with Docker

### Local stack

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- MLflow: http://localhost:5001
- SQLite UI: http://localhost:8080

### Production compose

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## MLflow Dashboard

Open: http://localhost:5001

Track each LLM call for latency, token usage, response size, prompt version, and user/session tags.

## CI/CD

Workflow file:

- .github/workflows/ci.yml

Behavior:

- Pull requests: lint + test
- Push to main: lint + test + build + deploy stage

For VPS deploy stage, add these repository secrets:

- VPS_HOST
- VPS_USER
- VPS_SSH_KEY

## Notes for GitHub Push

This workspace can be pushed to:

- https://github.com/Khan-Feroz211/EliteCSS-AI.git

Before push, ensure backend/.env is not committed and use .env.example as template.
