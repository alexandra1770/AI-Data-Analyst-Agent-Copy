\# AI Data Analyst Agent



\*\*An AI-powered data analytics application built with LangGraph, Groq, PostgreSQL, FastAPI, and React.\*\*



AI Data Analyst Agent allows users to explore e-commerce data using natural-language questions. The application combines an LLM-powered agent with database querying, Python-based analysis, interactive visualizations, and report generation.



\## Key Features



\- \*\*Natural Language Analytics\*\* — Ask business questions without writing SQL manually.

\- \*\*AI Agent with LangGraph\*\* — Coordinate analytical tasks using a stateful agent workflow.

\- \*\*PostgreSQL Integration\*\* — Analyze structured e-commerce data stored in a relational database.

\- \*\*Read-Only SQL Access\*\* — Use a restricted database role and SQL validation to reduce the risk of unauthorized modifications.

\- \*\*Python Data Analysis\*\* — Process query results and perform analytical calculations.

\- \*\*Data Visualization\*\* — Generate charts to communicate trends and business insights.

\- \*\*Report Generation\*\* — Export analysis results as Markdown reports.

\- \*\*React Dashboard\*\* — Interact with the agent and view analytical results through a web interface.

\- \*\*Automated Testing\*\* — Validate application behavior with Pytest.

\- \*\*CI/CD Pipeline\*\* — Run automated tests and publish Docker images using GitHub Actions.



\## Technology Stack



| Layer | Technologies |

|---|---|

| AI Agent | LangGraph, Groq LLM |

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



The project uses the Brazilian E-Commerce Public Dataset by Olist.



The local development database contains 99,441 order records, supporting the exploration of business metrics and e-commerce trends.



Example analytical questions:



\- What is the total revenue?

\- How does revenue change from month to month?

\- What are the monthly sales trends?

\- Generate a chart of monthly revenue.

\- Create a report summarizing sales performance.



\## API



The FastAPI backend exposes endpoints for application interaction and monitoring.



| Endpoint | Description |

|---|---|

| `GET /health` | Application health check |

| `POST /analyze` | Submit a natural-language analytical question |

| `GET /monitoring/status` | Application and service status |

| `GET /dashboard/stats` | Dashboard statistics |



Generated charts and reports can also be accessed through the backend's configured static routes.



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



Configure a local `.env` file with the required database connection settings and Groq API key.



```dotenv

DB\_HOST=localhost

DB\_PORT=5432

DB\_NAME=ai\_data\_analyst

DB\_USER=your\_readonly\_user

DB\_PASSWORD=your\_database\_password

GROQ\_API\_KEY=your\_groq\_api\_key

```



The PostgreSQL database must be initialized separately. The example CI database contains only a minimal test schema and is not a replacement for the analytical dataset.



Start the backend:



```bash

uvicorn api.main:app --reload

```



Backend URL: `http://localhost:8000`



\### Frontend Setup



Open a second terminal:



```bash

cd frontend

npm install

npm run dev

```



Frontend URL: `http://localhost:5173`



\### Docker



The backend can also be started with Docker Compose:



```bash

docker compose up --build -d

```



The Compose configuration is intended for local development and uses the database connection defined in the local environment.



\## Automated Testing



Run the test suite:



```bash

python -m pytest -q

```



The project includes tests covering API endpoints, agent behavior, database connectivity, SQL security, analytical tools, chart generation, and report exports.



\## CI/CD



GitHub Actions automatically runs on pushes and pull requests targeting the `main` branch.



The pipeline:



1\. Starts a temporary PostgreSQL service.

2\. Initializes a minimal test database.

3\. Installs Python dependencies.

4\. Runs the automated test suite.

5\. Builds the backend Docker image.

6\. Publishes the image to GitHub Container Registry on pushes to `main`.



\*\*Container image:\*\*



```text

ghcr.io/alexandra1770/ai-data-analyst-agent-copy:latest

```



The container package is currently private and requires authorization to download.



\## Security



The application incorporates several database security measures:



\- A restricted PostgreSQL role for read-only analytical access.

\- SQL query validation.

\- Environment-based configuration for credentials.

\- Exclusion of local `.env` files from Git and Docker builds.

\- Isolated PostgreSQL test credentials in GitHub Actions.



The application should be deployed with appropriate authentication, resource limits, and API usage protections before being exposed to unrestricted public traffic.



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

\- Improved observability and structured logging

\- Automated evaluation of analytical responses

\- Expanded dashboard capabilities

\- Support for additional data sources



\## Author



Developed by \*\*Alexandra Popii\*\*.



GitHub: \[alexandra1770](https://github.com/alexandra1770)



\---



\*An AI engineering portfolio project demonstrating agentic workflows, natural-language data analysis, backend development, database security, automated testing, and containerized CI/CD.\*

