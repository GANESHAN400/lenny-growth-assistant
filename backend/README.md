# Lenny Growth Assistant - Backend Service

Production-grade backend service powering the **Lenny Growth Assistant** AI platform.

---

## 1. Project Overview

The backend service for **Lenny Growth Assistant** is an evolving, production-grade Python application built using FastAPI and Python 3.12.

The backend is currently in the initial foundation sprint of development. As implementation progresses across planned sprints, the service will provide RESTful API endpoints, asynchronous agent execution workflows, retrieval pipelines, and persistence services supporting product and growth strategy inquiries.

---

## 2. Architecture

The application adheres to **Clean / Layered Architecture** principles, ensuring strict separation of concerns, high testability, and maintainability:

```
+-------------------------------------------------------------------+
|                        Presentation Layer                         |
|                     (app/api/ - Routers, Middleware)              |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                       Business Logic Layer                        |
|              (app/services/ - Core Domain & Orchestration)        |
+-------------------------------------------------------------------+
         |                                                 |
         v                                                 v
+-----------------------------------+    +-----------------------------------+
|          AI & RAG Engine          |    |         Data Access Layer       |
| (app/agents, rag, providers)      |    | (app/repositories, models)        |
+-----------------------------------+    +-----------------------------------+
                                                           |
                                                           v
                                         +-----------------------------------+
                                         |         Database Layer            |
                                         | (app/database/ - ORM & Connection)|
                                         +-----------------------------------+
```

- **API Layer (`app/api/`):** Handles incoming requests, validation via Pydantic schemas, dependency injection, and middleware.
- **Service Layer (`app/services/`):** Encapsulates core business logic and orchestrates application operations.
- **Repository Layer (`app/repositories/`):** Encapsulates data retrieval and persistence logic using the Repository Pattern.
- **AI Core (`app/agents/`, `app/rag/`, `app/providers/`):** Modular abstractions for AI execution, prompt templates, and data retrieval.

---

## 3. Engineering Principles

The codebase is built around foundational software engineering principles to maintain high quality and reliability:

- **Clean Architecture:** Strict separation between presentation, domain logic, data access, and infrastructure layers.
- **SOLID Principles:** Single responsibility modules, open/closed extension patterns, interface segregation, and dependency inversion.
- **Repository Pattern:** Decoupling business logic from persistence implementation details.
- **Dependency Injection:** Explicit dependency wiring using FastAPI's dependency injection system to improve testability.
- **Type Safety:** Comprehensive static typing enforced using Python type hints and strict MyPy analysis.
- **Production Readiness:** Standardized logging, structured error handling, strict linting, formatting, and automated quality checks.

---

## 4. Technology Stack

The backend technology stack currently configured in `pyproject.toml` includes:

| Category | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Language** | Python | `>=3.12,<4.0` | Modern, high-performance Python runtime |
| **Package Manager** | Poetry | `^1.8` | Dependency management & environment isolation |
| **Web Framework** | FastAPI | `^0.115.0` | Asynchronous web framework with automatic OpenAPI docs |
| **ASGI Server** | Uvicorn (`standard`) | `^0.30.0` | High-speed ASGI server implementation |
| **Data Validation** | Pydantic | `^2.8.0` | Type-safe data validation and schema definitions |
| **Settings Management**| Pydantic-Settings | `^2.4.0` | Environment variable parsing and configuration models |
| **Environment Parsing**| Python-Dotenv | `^1.0.1` | `.env` file management for local development |
| **HTTP Client** | HTTPX | `^0.27.0` | Fully async HTTP client for external service integration |
| **Structured Logging** | Loguru | `^0.7.2` | Contextual logging without boilerplate |
| **JSON Parser** | Orjson | `^3.10.0` | Ultra-fast JSON serialization |
| **Code Formatter** | Black | `^24.4.2` | Opinionated code formatter |
| **Linter / Imports** | Ruff | `^0.5.0` | Fast Python linter and import sorter |
| **Static Type Checker**| MyPy | `^1.10.0` | Strict static type checking |
| **Testing Framework** | Pytest / Pytest-Asyncio| `^8.2.2` / `^0.23.7` | Asynchronous test execution suite |
| **Git Hooks** | Pre-Commit | `^3.7.1` | Automated pre-commit quality checks |

---

## 5. Directory Structure

The backend application code resides inside `backend/app/` with the following folder taxonomy:

| Folder | Description & Responsibility |
| :--- | :--- |
| `app/agents/` | Multi-agent execution loops, ReAct agents, tool definitions, and task orchestrators. |
| `app/api/` | API routing layer, including `routers/` (endpoints), `middleware/`, and `dependencies/`. |
| `app/core/` | Application configuration, shared constants, and core utilities. |
| `app/database/` | Database engine initialization, session factory management, and migrations. |
| `app/models/` | Relational database ORM entities and database table definitions. |
| `app/prompts/` | Centralized system prompts, agent personas, and dynamic prompt templates. |
| `app/providers/` | Integration clients for external services and model providers. |
| `app/rag/` | Retrieval-Augmented Generation core: chunker, embedder, indexer, and search retriever. |
| `app/repositories/` | Data access abstraction layer implementing the Repository Pattern. |
| `app/schemas/` | Pydantic models for API request validation, response serialization, and DTOs. |
| `app/services/` | Application service layer containing core business logic and orchestration. |
| `app/tests/` | Automated test suite comprising unit tests, integration tests, and fixtures. |
| `app/utils/` | Utility functions, custom helpers, text formatters, and reusable tools. |

---

## 6. Development Setup

### Prerequisites

Ensure the following tools are installed on your environment before starting:

- **Python:** `>=3.12,<4.0` (Python 3.12.x recommended)
- **Poetry:** `1.8+` ([Poetry Installation Guide](https://python-poetry.org/docs/#installation))
- **Git:** Latest stable release

---

## 7. Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/GANESHAN400/lenny-growth-assistant.git
   cd lenny-growth-assistant/backend
   ```

2. **Verify Python Version:**
   ```bash
   python --version
   # Expected output: Python 3.12.x
   ```

3. **Install Dependencies:**
   Install all runtime and development dependencies using Poetry:
   ```bash
   poetry install
   ```

4. **Activate Virtual Environment:**
   ```bash
   poetry shell
   ```

---

## 8. Running the Development Server

> **Note:** Server entrypoint implementation (`app/main.py`) will be completed in subsequent implementation milestones.

Once server setup is finalized, launch the development server using Uvicorn:

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 9. Code Quality

The project enforces strict code formatting, linting, type safety, and testing standards. Run the following commands prior to submitting code:

```bash
# Code Formatting (Black)
poetry run black app

# Linting & Import Sorting (Ruff)
poetry run ruff check app

# Static Type Checking (MyPy)
poetry run mypy app

# Test Execution (Pytest)
poetry run pytest
```

To automate checks before every Git commit:
```bash
poetry run pre-commit install
```

---

## 10. Current Status

| Sprint | Task | Description | Status |
| :--- | :--- | :--- | :--- |
| **Sprint 1 (Backend Foundation)** | Task 2.1 | Configure Poetry `pyproject.toml` with runtime & dev dependencies and tool configs | ✅ Completed |
| **Sprint 1 (Backend Foundation)** | Task 2.2 | Create professional backend `README.md` documentation | ✅ Completed |

---

## 11. Upcoming Tasks

| Sprint | Target Focus | Objective |
| :--- | :--- | :--- |
| **Sprint 1** | Application Entrypoint Setup | Implement `backend/app/main.py` with FastAPI initialization & health check endpoints |
| **Sprint 1** | Configuration & Settings Module | Implement `backend/app/core/config.py` using `pydantic-settings` |
| **Sprint 2** | Database Layer Infrastructure | Configure database connection factory, base model, and repositories |
| **Sprint 2** | RAG Pipeline Foundation | Ingestion pipeline, chunking strategies, and vector storage integration |
