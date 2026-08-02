# 🚀 Lenny Growth Assistant

> **An AI-powered product growth strategy advisor**, grounded in Lenny Rachitsky's podcast transcripts. Ask anything about growth loops, activation, retention, monetization, virality — and get sharp, transcript-backed answers in real time.

![Lenny Growth Assistant](assets/banner.png)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Q&A Mode** | RAG-grounded answers strictly from Lenny's podcast transcripts |
| ✍️ **Ship30 Essays** | Ship30for30-style essays (~1,250 words) on any growth topic |
| 🎨 **Artifact Generator** | Generates full HTML dashboards or Markdown documents with in-app preview |
| 🧠 **Auto Skill Detection** | The agent detects the best skill automatically from your message |
| 💬 **Streaming Responses** | Real-time token streaming via Server-Sent Events (SSE) |
| 🗂️ **Session Management** | Persistent chat history across sessions, auto-generated titles |
| 🔧 **Dual LLM Provider** | Supports **Ollama** (local, free) and **Anthropic Claude** (cloud) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (HTML/CSS/JS)                     │
│         Chat UI · Session Sidebar · Artifact Viewer             │
└─────────────────────────┬───────────────────────────────────────┘
                          │ SSE + REST
┌─────────────────────────▼───────────────────────────────────────┐
│                    FastAPI Backend (Python 3.12)                 │
│                                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐ │
│  │  API Routers │  │  Service Layer   │  │  Schema Validation │ │
│  │  /chat       │  │  ChatService     │  │  Pydantic v2       │ │
│  │  /sessions   │  │  SessionService  │  │                    │ │
│  └──────┬───────┘  └────────┬─────────┘  └────────────────────┘ │
│         │                  │                                     │
│  ┌──────▼──────────────────▼─────────────────────────────────┐  │
│  │                  Growth Agent Orchestrator                  │  │
│  │   ┌──────┐  ┌────────┐  ┌──────────┐  ┌───────────────┐  │  │
│  │   │ Q&A  │  │ Ship30 │  │ Artifact │  │  Chat (base)  │  │  │
│  │   └──────┘  └────────┘  └──────────┘  └───────────────┘  │  │
│  └──────────┬────────────────────────────────────────────────┘  │
│             │                                                    │
│  ┌──────────▼──────────┐  ┌─────────────────────────────────┐  │
│  │   LLM Providers     │  │     RAG Pipeline (BM25)         │  │
│  │  Ollama · Anthropic │  │  Chunker · Indexer · Retriever  │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Repository Layer (SQLAlchemy)                  │  │
│  │         ChatSessionRepository · MessageRepository        │  │
│  └────────────────────────────┬─────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  SQLite (dev)          │
                    │  PostgreSQL (prod)     │
                    └───────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation) 1.8+
- [Ollama](https://ollama.ai) (for local LLM) — or Anthropic API key

### 1. Clone & Install

```bash
git clone https://github.com/GANESHAN400/lenny-growth-assistant.git
cd lenny-growth-assistant
```

### 2. Configure Environment

```bash
cp .env.example backend/.env
# Edit backend/.env with your settings
```

### 3. Install Backend Dependencies

```bash
cd backend
poetry install
```

### 4. Run Database Migrations

```bash
poetry run alembic upgrade head
```

### 5. (Optional) Pull Lenny Transcripts for RAG

```bash
poetry run python -m app.rag.ingest
```

### 6. Start the Backend

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Open the Frontend

Open `frontend/index.html` in your browser (or serve it with any static file server):

```bash
# Using Python's built-in server from the project root:
cd frontend && python -m http.server 3000
# Then open http://localhost:3000
```

---

## ⚙️ Configuration

Copy `.env.example` to `backend/.env` and set the following:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+pysqlite:///./lenny.db` | Database connection string |
| `DEFAULT_PROVIDER` | `ollama` | LLM provider (`ollama` or `anthropic`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Default Ollama model |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic API key (required for Claude) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 🧠 Skills Explained

### 🔍 Q&A (RAG-Grounded)
Retrieves relevant chunks from Lenny's podcast transcripts using BM25 keyword search, then answers strictly from those sources. Best for: *"What did X say about Y?"*

### ✍️ Ship30for30 Essays
Generates 1,250-word essays in the Ship30for30 atomic essay format — hook, bold subheadings, bullet points, concrete examples. Best for: *"Write an essay on activation mistakes"*

### 🎨 Artifact Generator
Generates complete, self-contained HTML pages or Markdown documents. Best for: *"Create an AARRR metrics dashboard"*

### 🧠 Auto Mode
The agent uses LLM-based skill detection to automatically route your message to the best skill. You can override it manually in the sidebar.

---

## 🛠️ Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — Async web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/) — ORM & migrations
- [Pydantic v2](https://docs.pydantic.dev/) — Schema validation
- [Loguru](https://loguru.readthedocs.io/) — Structured logging
- [HTTPX](https://www.python-httpx.org/) — Async HTTP client

**AI / ML**
- [Ollama](https://ollama.ai/) — Local LLM serving (Qwen, Llama, Mistral, etc.)
- [Anthropic Python SDK](https://github.com/anthropic-ai/anthropic-sdk-python) — Claude models
- Custom BM25 retriever (no heavy vector DB required)

**Frontend**
- Vanilla HTML/CSS/JS — zero framework, fast loading
- Server-Sent Events (SSE) for real-time streaming
- `marked.js` for Markdown rendering

---

## 📁 Project Structure

```
lenny-growth-assistant/
├── backend/                    # FastAPI backend service
│   ├── app/
│   │   ├── agents/             # Growth agent orchestrator
│   │   ├── api/
│   │   │   ├── middleware/     # CORS, exception handlers
│   │   │   └── routers/        # chat, sessions, health endpoints
│   │   ├── core/               # Config, logging
│   │   ├── database/           # SQLAlchemy engine, session, base
│   │   ├── models/             # ORM models (ChatSession, ChatMessage)
│   │   ├── prompts/            # Lenny system prompt & templates
│   │   ├── providers/          # Ollama & Anthropic LLM clients
│   │   ├── rag/                # BM25 chunker, ingest, retriever
│   │   ├── repositories/       # Data access layer
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic (chat, session)
│   │   └── main.py             # FastAPI entrypoint
│   ├── alembic/                # Database migrations
│   ├── data/
│   │   └── transcripts/        # Lenny podcast transcripts (.txt)
│   ├── pyproject.toml
│   └── .env                    # Local config (gitignored)
├── frontend/                   # Static HTML/CSS/JS UI
│   ├── index.html
│   ├── style.css
│   └── app.js
├── docs/                       # Architecture & design docs
├── .env.example                # Environment variable template
└── README.md
```

---

## 📚 Documentation

Detailed docs are in the [`docs/`](docs/) directory:

- [`PRD.md`](docs/PRD.md) — Product Requirements Document
- [`architecture.md`](docs/architecture.md) — System Architecture
- [`api-design.md`](docs/api-design.md) — API Reference
- [`database-design.md`](docs/database-design.md) — Database Schema
- [`design.md`](docs/design.md) — UI/UX Design
- [`implementation-roadmap.md`](docs/implementation-roadmap.md) — Roadmap

---

## 🧪 Running Tests

```bash
cd backend
poetry run pytest app/tests/ -v
```

---

## 📄 License

[MIT License](LICENSE) — see [LICENSE](LICENSE) for details.
