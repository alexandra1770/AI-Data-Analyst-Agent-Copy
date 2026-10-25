\# AI Data Analyst Agent



\*\*An AI-powered data analytics application built with LangGraph, Groq, PostgreSQL, FastAPI, and React.\*\*



AI Data Analyst Agent allows users to explore e-commerce data using natural-language questions. It combines an LLM-powered agent with SQL querying, Python-based analysis, chart generation, and report exports.



\## Key Features



\- \*\*Natural Language Analytics\*\* — Ask business questions without manually writing SQL.

\- \*\*LangGraph AI Agent\*\* — Coordinate analytical tasks using a stateful agent workflow.

\- \*\*PostgreSQL Integration\*\* — Query structured e-commerce data.

\- \*\*Read-Only SQL Access\*\* — Use a restricted database role and SQL validation to reduce the risk of data modification.

\- \*\*Python Data Analysis\*\* — Process query results and perform analytical calculations.

\- \*\*Data Visualization\*\* — Generate charts for business trends and insights.

\- \*\*Report Generation\*\* — Export analysis results as Markdown reports.

\- \*\*React Dashboard\*\* — Ask questions and view results through a web interface.

\- \*\*Automated Testing\*\* — Test application behavior with Pytest.

\- \*\*CI/CD\*\* — Test, build, and publish Docker images with GitHub Actions.



\## Technology Stack



| Layer | Technologies |

| --- | --- |

| AI Agent | LangGraph, Groq |

| Backend | Python, FastAPI |

| Database | PostgreSQL, SQLAlchemy |

| Data Analysis | Pandas |

| Visualization | Matplotlib |

| Frontend | React, Vite |

| Containerization | Docker, Docker Compose |

| Testing | Pytest |

| CI/CD | GitHub Actions |

| Container Registry | GitHub Container Registry (GHCR) |



\## System Architecture



```text

User

&#x20; |

&#x20; v

React Frontend

&#x20; |

&#x20; v

FastAPI Backend

&#x20; |

&#x20; v

LangGraph AI Agent

&#x20; |

&#x20; +-- Inspect Database Schema

&#x20; |

&#x20; +-- Validate and Execute SQL Queries

&#x20; |       |

&#x20; |       v

&#x20; |    PostgreSQL

&#x20; |

&#x20; +-- Python Data Analysis

&#x20; |

&#x20; +-- Chart Generation

&#x20; |

&#x20; +-- Report Generation

&#x20; |

&#x20; v

Response to User

```



\## Dataset



The project uses the \*\*Brazilian E-Commerce Public Dataset by Olist\*\*.



The local development database contains \*\*99,441 order records\*\*, enabling exploration of sales trends and business metrics.



Example questions:



\- What is the total revenue?

\- How does revenue change from month to month?

\- What are the monthly sales trends?

\- Generate a chart of monthly revenue.

\- Create a report summarizing sales performance.



\## API



| Endpoint | Description |

| --- | --- |

| `GET /` | Root endpoint |

| `GET /health` | Application health check |

| `POST /analyze` | Submit a natural-language analytical question |

| `GET /monitoring/status` | Application and service status |

| `GET /dashboard/stats` | Dashboard statistics |

| `GET /reports/list` | List generated reports |



The backend also serves generated charts and reports through configured static routes.



\## Local Development



\### Prerequisites



\- Python 3.10

\- PostgreSQL

\- Node.js and npm

\- Git

\- Docker Desktop (optional)



\### Backend Setup



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

DB\_HOST=localhost

DB\_PORT=5432

DB\_NAME=ai\_data\_analyst

DB\_USER=your\_readonly\_user

DB\_PASSWORD=your\_database\_password

GROQ\_API\_KEY=your\_groq\_api\_key

```



\*\*Never commit your `.env` file or real API keys.\*\*



The analytical PostgreSQL database must be initialized separately. The minimal database schema used by CI is intended for automated tests, not full analytics.



Start the backend:



```bash

uvicorn api.main:app --reload

```



Backend URL: `http://localhost:8000`



\### Frontend Setup



In a second terminal:



```bash

cd frontend

npm install

npm run dev

```



Frontend URL: `http://localhost:5173`



\### Docker



To start the backend with Docker Compose:



```bash

docker compose up --build -d

```



The local Compose setup uses environment variables from `.env` and connects to the PostgreSQL instance configured for local development.



\## Automated Testing



Run the tests:



```bash

python -m pytest -q

```



The test suite covers API endpoints, agent behavior, database connectivity, SQL validation, analysis tools, chart generation, and report exports. Database integration tests require an available PostgreSQL instance.



\## CI/CD



GitHub Actions runs on pushes and pull requests targeting `main`.



The workflow:



1\. Starts a temporary PostgreSQL service.

2\. Initializes a minimal test database.

3\. Installs Python dependencies.

4\. Runs the automated tests.

5\. Builds the backend Docker image.

6\. Publishes the image to GHCR on pushes to `main`.



\*\*Container image:\*\*



```text

ghcr.io/alexandra1770/ai-data-analyst-agent-copy:latest

```



The GHCR package is currently private and requires authorization to download.



\## Security



\- A restricted PostgreSQL role supports read-only analytical access.

\- SQL validation provides an additional safeguard against unsafe queries.

\- Credentials are configured through environment variables.

\- Local `.env` files are excluded from Git and Docker builds.

\- GitHub Actions uses isolated PostgreSQL test credentials.



Before opening a public demo to unrestricted traffic, add appropriate authentication, request limits, and API usage protections.



\## Deployment Status



\- \[x] Local application development

\- \[x] PostgreSQL integration

\- \[x] Docker containerization

\- \[x] Automated testing

\- \[x] GitHub Actions CI

\- \[x] GHCR image publishing

\- \[ ] Cloud PostgreSQL configuration

\- \[ ] Backend cloud deployment

\- \[ ] Frontend cloud deployment

\- \[ ] Public live demo



\## Future Improvements



\- Cloud deployment and public demo

\- Structured logging and monitoring

\- Automated evaluation of analytical responses

\- Expanded dashboard capabilities

\- Support for additional data sources



\## Author



Developed by \*\*Alexandra Popii\*\*.



GitHub: \[alexandra1770](https://github.com/alexandra1770)



\---



\*An AI engineering portfolio project demonstrating agentic workflows, natural-language data analysis, backend development, database security, automated testing, and containerized CI/CD.\*



