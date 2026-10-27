# AI Data Analyst Agent

**An AI-powered data analytics application built with LangGraph, Groq, Model Context Protocol (MCP), PostgreSQL, FastAPI, and React.**

AI Data Analyst Agent allows users to explore e-commerce data using natural-language questions. It combines an LLM-powered agent with MCP-based database tools, SQL querying, Python-based analysis, chart generation, and report exports.

## Key Features

- **Natural Language Analytics** — Ask business questions without manually writing SQL.
- **LangGraph AI Agent** — Coordinate analytical tasks using a stateful agent workflow.
- **PostgreSQL Integration** — Query structured e-commerce data.
- **MCP Integration** — Inspect the database schema and execute validated SQL queries through a dedicated MCP server and client.
- **Read-Only SQL Access** — Use a restricted database role and SQL validation to reduce the risk of data modification.
- **Input and Output Guardrails** — Apply safeguards to incoming questions and generated responses.
- **Langfuse Observability** — Trace and inspect agent execution.
- **LLM Evaluation** — Check analytical responses against reference SQL results.
- **Python Data Analysis** — Process query results and perform analytical calculations.
- **Data Visualization** — Generate charts for business trends and insights.
- **Report Generation** — Export analysis results as Markdown reports.
- **React Dashboard** — Ask questions and view results through a web interface.
- **Automated Testing** — Test application behavior with Pytest.
- **CI/CD** — Test, build, and publish Docker images with GitHub Actions.

## Technology Stack

| Layer | Technologies |
| --- | --- |
| AI Agent | LangGraph, Groq |
| Database Tool Protocol | MCP (Python SDK), FastMCP |
| Observability | Langfuse |
| Backend | Python, FastAPI |
| Database | PostgreSQL, SQLAlchemy |
| Data Analysis | Pandas |
| Visualization | Matplotlib |
| Frontend | React, Vite |
| Containerization | Docker, Docker Compose |
| Testing | Pytest |
| CI/CD | GitHub Actions |
| Container Registry | GitHub Container Registry (GHCR) |

## System Architecture

```text
User
  |
  v
React Frontend
  |
  v
FastAPI Backend
  |
  v
Input Guardrails
  |
  v
LangGraph AI Agent <----> Groq LLM
  |
  +-- MCP Client (stdio)
  |     |
  |     v
  |   MCP Server
  |     +-- Inspect Database Schema and Foreign Keys
  |     +-- Validate and Execute Read-Only SQL
  |               |
  |               v
  |           PostgreSQL
  |
  +-- Python Data Analysis
  +-- Chart Generation
  +-- Report Generation
  |
  v
Output Guardrails
  |
  v
Response to User

Langfuse traces agent execution and tool activity.
```

## MCP Integration

The project uses **Model Context Protocol (MCP)** to separate database tooling from the LangGraph agent. The agent connects to a local MCP server over **stdio** through `src/mcp_server/client.py`.

The MCP server (`src/mcp_server/server.py`) exposes two tools:

| MCP Tool | Purpose |
| --- | --- |
| `inspect_database_schema` | Return allowlisted PostgreSQL tables, columns, and foreign-key relationships. |
| `execute_database_query` | Execute SQL through the project's existing read-only query validation and return structured results. |

The SQL tool returns `columns`, `rows`, and `row_count`, allowing the agent and API to preserve structured query results for downstream analysis. SQL validation and read-only database access remain enforced; MCP does not bypass the security layer.

The MCP server is launched automatically by the client when a database tool is called. It is not necessary to start a separate server manually for normal local agent use.

## Dataset

The project uses the **Brazilian E-Commerce Public Dataset by Olist**.

The local development database contains **99,441 order records**, enabling exploration of sales trends and business metrics.

Example questions:

- What is the total revenue?
- How does revenue change from month to month?
- What are the monthly sales trends?
- Generate a chart of monthly revenue.
- Create a report summarizing sales performance.

## API

| Endpoint | Description |
| --- | --- |
| `GET /` | Root endpoint |
| `GET /health` | Application health check |
| `POST /analyze` | Submit a natural-language analytical question |
| `GET /monitoring/status` | Application and service status |
| `GET /dashboard/stats` | Dashboard statistics |
| `GET /reports/list` | List generated reports |

The backend also serves generated charts and reports through configured static routes.

## Local Development

### Prerequisites

- Python 3.10
- PostgreSQL
- Node.js and npm
- Git
- Docker Desktop (optional)

### Backend Setup

Clone the repository:

```bash
git clone https://github.com/alexandra1770/AI-Data-Analyst-Agent-Copy.git
cd AI-Data-Analyst-Agent-Copy
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create a local `.env` file with your own database credentials and Groq API key:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_data_analyst
DB_USER=your_readonly_user
DB_PASSWORD=your_database_password
GROQ_API_KEY=your_groq_api_key
```

**Never commit your `.env` file or real API keys.**

The analytical PostgreSQL database must be initialized separately. The minimal database schema used by CI is intended for automated tests, not full analytics.

Start the backend:

```bash
uvicorn api.main:app --reload
```

Backend URL: `http://localhost:8000`

### Frontend Setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173`

### Docker

To start the backend with Docker Compose:

```bash
docker compose up --build -d
```

The local Compose setup uses environment variables from `.env` and connects to the PostgreSQL instance configured for local development.

## Automated Testing

Run the tests:

```bash
python -m pytest -q
```

The test suite covers API endpoints, agent behavior, database connectivity, SQL validation, input/output guardrails, MCP server tools, analysis tools, chart generation, and report exports. Database integration tests require an available PostgreSQL instance.

Three MCP protocol integration tests in `tests/test_mcp_protocol.py` start a real MCP subprocess and require a working PostgreSQL configuration. They are **skipped by default**, including in the current GitHub Actions workflow. To run them locally with PostgreSQL configured:

**Windows Command Prompt / Anaconda Prompt:**

```bat
set RUN_MCP_INTEGRATION_TESTS=1
python -m pytest tests/test_mcp_protocol.py -q
set RUN_MCP_INTEGRATION_TESTS=
```

**Linux / macOS:**

```bash
RUN_MCP_INTEGRATION_TESTS=1 python -m pytest tests/test_mcp_protocol.py -q
```

The current CI workflow validates the remaining test suite, but does not yet exercise the real MCP subprocess-to-PostgreSQL path.

## CI/CD

GitHub Actions runs on pushes and pull requests targeting `main`.

The workflow:

1. Starts a temporary PostgreSQL service.
2. Initializes a minimal test database.
3. Installs Python dependencies.
4. Runs the automated tests (MCP protocol integration tests are skipped unless explicitly enabled).
5. Builds the backend Docker image.
6. Publishes the image to GHCR on pushes to `main`.

**Container image:**

```text
ghcr.io/alexandra1770/ai-data-analyst-agent-copy:latest
```

The GHCR package is currently private and requires authorization to download.

## Security

- A restricted PostgreSQL role supports read-only analytical access.
- SQL validation provides an additional safeguard against unsafe queries.
- SQL guardrails restrict queries to permitted read-only operations and approved database objects.
- Input and output guardrails add safeguards around agent requests and responses.
- MCP database access reuses the existing SQL validation layer.
- Credentials are configured through environment variables.
- Local `.env` files are excluded from Git and Docker builds.
- GitHub Actions uses isolated PostgreSQL test credentials.

Before opening a public demo to unrestricted traffic, add appropriate authentication, request limits, and API usage protections.

## Deployment Status

- [x] Local application development
- [x] PostgreSQL integration
- [x] MCP server and LangGraph client integration
- [x] SQL, input, and output guardrails
- [x] Langfuse observability
- [x] Docker containerization
- [x] Automated testing
- [x] GitHub Actions CI
- [x] GHCR image publishing
- [ ] Cloud PostgreSQL configuration
- [ ] Backend cloud deployment
- [ ] Frontend cloud deployment
- [ ] Public live demo

## Future Improvements

- Cloud deployment and public demo
- Expanded structured logging and monitoring
- Extend automated analytical evaluation and regression coverage
- Run MCP protocol integration tests against an isolated PostgreSQL service in CI
- Expanded dashboard capabilities
- Support for additional data sources

## Author

Developed by **Alexandra Popii**.

GitHub: [alexandra1770](https://github.com/alexandra1770)

---

*An AI engineering portfolio project demonstrating agentic workflows, natural-language data analysis, backend development, MCP-based database tools, database security, observability, automated testing, and containerized CI/CD.*
