
# Creating FastAPI application

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import text

from src.agent import agent
from src.database import engine


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
            result = connection.execute(
                text(
                    """
                    SELECT
                        (SELECT COALESCE(SUM(price), 0)
                         FROM order_items) AS total_revenue,
                        (SELECT COUNT(*) FROM orders) AS total_orders,
                        (SELECT COUNT(*) FROM products) AS total_products,
                        (SELECT COUNT(*) FROM sellers) AS total_sellers
                    """
                )
            ).mappings().one()

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
    try:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": request.question
                    }
                ]
            }
        )

        final_message = result["messages"][-1]

        charts = []
        reports = []

        for message in result["messages"]:
            if message.type != "tool":
                continue

            if message.name == "create_chart":
                if "CHART_ERROR" not in str(message.content):
                    chart_filename = Path(str(message.content)).name

                    charts.append(
                        f"/charts/{chart_filename}"
                    )

            elif message.name == "export_report":
                if "REPORT_ERROR" not in str(message.content):
                    report_filename = Path(str(message.content)).name

                    reports.append(
                        f"/reports/{report_filename}"
                    )

        return {
            "question": request.question,
            "answer": final_message.content,
            "charts": charts,
            "reports": reports
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/monitoring/status")
def monitoring_status():
    database_status = "offline"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
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

