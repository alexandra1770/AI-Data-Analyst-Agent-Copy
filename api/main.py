
# Creating FastAPI application

from pathlib import Path
from uuid import UUID, uuid4

from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler

from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from sqlalchemy import text

from src.agent import agent
from src.database import engine
from src.guardrails.input_guardrails import validate_user_input


# Incarca variabilele de mediu, inclusiv cheile Langfuse
load_dotenv()


app = FastAPI(
    title="AI Data Analyst Agent API",
    description="API for interacting with the AI Data Analyst Agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)

BASE_DIR = Path(__file__).resolve().parent.parent


@app.get("/reports/list")
def list_reports():
    reports_directory = BASE_DIR / "outputs" / "reports"

    if not reports_directory.exists():
        return {"reports": [], "total": 0}

    reports = []

    for file in reports_directory.glob("*.md"):
        if not file.is_file():
            continue

        reports.append({
            "filename": file.name,
            "name": file.stem.replace("_", " ").title(),
            "url": f"/reports/{file.name}",
            "size_kb": round(file.stat().st_size / 1024, 2),
            "created_at": file.stat().st_mtime
        })

    reports.sort(
        key=lambda report: report["created_at"],
        reverse=True
    )

    return {
        "reports": reports,
        "total": len(reports)
    }


app.mount(
    "/charts",
    StaticFiles(directory=BASE_DIR / "outputs" / "charts"),
    name="charts"
)

app.mount(
    "/reports",
    StaticFiles(directory=BASE_DIR / "outputs" / "reports"),
    name="reports"
)


class AnalysisRequest(BaseModel):
    question: str

    # Optional for backward compatibility with existing API clients and tests.
    conversation_id: str | None = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, value):
        # Verifica intrebarea folosind Input Guardrails
        return validate_user_input(value)

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, value):
        if value is None:
            return None

        try:
            return str(UUID(value))
        except (ValueError, AttributeError, TypeError):
            raise ValueError(
                "conversation_id must be a valid UUID."
            )


@app.get("/")
def root():
    return {
        "message": "AI Data Analyst Agent API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.get("/dashboard/stats")
def get_dashboard_stats():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT
                    (SELECT COALESCE(SUM(price), 0)
                     FROM order_items) AS total_revenue,

                    (SELECT COUNT(*)
                     FROM orders) AS total_orders,

                    (SELECT COUNT(*)
                     FROM products) AS total_products,

                    (SELECT COUNT(*)
                     FROM sellers) AS total_sellers
            """)).mappings().one()

        return {
            "total_revenue": float(result["total_revenue"]),
            "total_orders": int(result["total_orders"]),
            "total_products": int(result["total_products"]),
            "total_sellers": int(result["total_sellers"]),
            "currency": "BRL"
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to load dashboard statistics."
        )


@app.post("/analyze")
def analyze(request: AnalysisRequest):

    # Genereaza un ID nou daca nu exista o conversatie anterioara
    conversation_id = request.conversation_id or str(uuid4())

    try:
        # Pastreaza configuratia existenta a agentului
        config = {
            "recursion_limit": 15
        }

        # Memoria LangGraph foloseste thread_id
        config["configurable"] = {
            "thread_id": conversation_id
        }

        # Initializeaza Langfuse pentru monitorizarea executiei
        langfuse_handler = CallbackHandler()

        # Inregistreaza apelurile LLM si instrumentele agentului
        config["callbacks"] = [
            langfuse_handler
        ]

        # Executa agentul LangGraph
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": request.question
                    }
                ]
            },
            config=config
        )

        messages = result["messages"]
        final_message = messages[-1]

        # Checkpointing returns the entire conversation.
        # Only expose artifacts produced after the latest user message.
        last_user_index = -1

        for index, message in enumerate(messages):
            if getattr(message, "type", None) == "human":
                last_user_index = index

        current_turn_messages = messages[
            last_user_index + 1:
        ]

        charts = []
        reports = []
        tables = []

        for message in current_turn_messages:
            if getattr(message, "type", None) != "tool":
                continue

            content = str(message.content).strip()

            if message.name == "execute_database_query":
                artifact = getattr(
                    message,
                    "artifact",
                    None
                )

                if isinstance(artifact, dict):
                    tables.append(
                        jsonable_encoder(artifact)
                    )

            elif message.name == "create_chart":
                chart_path = Path(content)

                if (
                    chart_path.suffix.lower() == ".png"
                    and "CHART_ERROR" not in content
                ):
                    charts.append(
                        f"/charts/{chart_path.name}"
                    )

            elif message.name == "export_report":
                report_path = Path(content)

                if (
                    report_path.suffix.lower() == ".md"
                    and "REPORT_ERROR" not in content
                ):
                    reports.append(
                        f"/reports/{report_path.name}"
                    )

        # Afiseaza ultimul rezultat SQL ca tabel principal
        primary_tables = tables[-1:] if tables else []
        intermediate_tables = tables[:-1]

        return {
            "question": request.question,
            "conversation_id": conversation_id,
            "answer": final_message.content,
            "charts": charts,
            "reports": reports,
            "tables": primary_tables,
            "intermediate_tables": intermediate_tables
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to complete the analysis."
        )


@app.get("/monitoring/status")
def monitoring_status():

    database_status = "offline"

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        database_status = "online"

    except Exception:
        pass

    charts_directory = BASE_DIR / "outputs" / "charts"
    reports_directory = BASE_DIR / "outputs" / "reports"

    charts_count = (
        len(list(charts_directory.glob("*.png")))
        if charts_directory.exists()
        else 0
    )

    reports_count = (
        len(list(reports_directory.glob("*.md")))
        if reports_directory.exists()
        else 0
    )

    return {
        "api": "online",
        "database": database_status,
        "agent": "loaded",
        "charts_generated": charts_count,
        "reports_generated": reports_count
    }
