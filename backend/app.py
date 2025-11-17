from __future__ import annotations

import re
import sys
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    from .config import get_settings
    from .database import Base, SessionLocal, engine
    from .models import LatteRun, BenchmarkRun, BenchmarkSnapshot
    from .mock_data import (
        SUITE_LABELS,
        _generate_suite_payload,
    )
    from .schemas import (
        ConfigResponse,
        LatteCreateRequest,
        LatteRollupResponse,
        LatteRunDetailResponse,
        LatteRunListResponse,
    )
    from .services.latte_service import create_latte_run, fetch_runs, get_rollups
except ImportError:  # pragma: no cover - direct execution fallback
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from backend.config import get_settings  # type: ignore[no-redef]
    from backend.database import Base, SessionLocal, engine  # type: ignore[no-redef]
    from backend.models import LatteRun, BenchmarkRun, BenchmarkSnapshot  # type: ignore[no-redef]
    from backend.mock_data import (  # type: ignore[no-redef]
        SUITE_LABELS,
        _generate_suite_payload,
    )
    from backend.schemas import (  # type: ignore[no-redef]
        ConfigResponse,
        LatteCreateRequest,
        LatteRollupResponse,
        LatteRunDetailResponse,
        LatteRunListResponse,
    )
    from backend.services.latte_service import create_latte_run, fetch_runs, get_rollups  # type: ignore[no-redef]

settings = get_settings()

MAX_HISTORY = 30

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Depends(api_key_header)) -> str | None:
    if settings.mock_mode:
        return api_key
    if api_key == settings.api_key:
        return api_key
    raise HTTPException(status_code=401, detail="Invalid API Key")

app = FastAPI(
    title="OmniBrew", version="0.1.0", description="Prompt Trace Scoring with OmniBAR"
)

origins = list(
    dict.fromkeys(
        (settings.allow_origins or [])
        + ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"message": "Welcome to OmniBrew"}


@app.get("/config", response_model=ConfigResponse, tags=["meta"])
def read_config() -> ConfigResponse:
    models = {settings.default_model, settings.scoring_model, "gpt-4o-mini", "gpt-4o"}
    return ConfigResponse(
        mock_mode=settings.mock_mode,
        default_model=settings.default_model,
        scoring_model=settings.scoring_model,
        available_models=sorted(models),
    )


@app.post(
    "/lattes", response_model=LatteRunDetailResponse, tags=["lattes"], status_code=201
)
def create_latte(
    payload: LatteCreateRequest, db: Session = Depends(get_db)
) -> LatteRun:
    if not payload.system_prompt.strip():
        raise HTTPException(status_code=400, detail="System prompt is required")
    if not payload.user_prompt.strip():
        raise HTTPException(status_code=400, detail="User prompt is required")

    run = create_latte_run(db, payload, settings=settings)
    db.refresh(run)
    return run


@app.get("/lattes", response_model=LatteRunListResponse, tags=["lattes"])
def list_lattes(db: Session = Depends(get_db)) -> LatteRunListResponse:
    runs = fetch_runs(db)
    return LatteRunListResponse(runs=runs)


@app.get("/lattes/{run_id}", response_model=LatteRunDetailResponse, tags=["lattes"])
def get_latte(run_id: int, db: Session = Depends(get_db)) -> LatteRun:
    run = db.query(LatteRun).filter(LatteRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Latte run not found")
    return run


@app.get("/analytics/rollups", response_model=LatteRollupResponse, tags=["analytics"])
def analytics_rollups(db: Session = Depends(get_db)) -> LatteRollupResponse:
    return get_rollups(db)


@app.post("/login", tags=["auth"])
def login(request: LoginRequest) -> dict[str, str]:
    if request.password == settings.password:
        return {"token": settings.api_key or "mock-api-key"}
    raise HTTPException(status_code=401, detail="Invalid password")


def generate_id() -> str:
    return str(uuid4())


def evaluate_objectives(input: AgentInput, output: AgentOutput) -> list[ObjectiveResult]:
    expected = str(input.a + input.b) if input.operation == 'add' else str(input.a * input.b) if input.operation == 'multiply' else 'error'
    objectives: list[ObjectiveResult] = []

    objectives.append(ObjectiveResult(
        id=generate_id(),
        name='Exact answer match',
        kind='stringEquals',
        success=output.answer == expected,
        details=f'Expected {expected}, got {output.answer}',
    ))

    regex = r'^(Adding|Multiplying) \d+ .* = \d+$'
    objectives.append(ObjectiveResult(
        id=generate_id(),
        name='Explanation format',
        kind='regexMatch',
        success=bool(re.match(regex, output.explanation)),
        details='Explanation must describe the math operation',
    ))

    return objectives


def simulate_agent(input: AgentInput) -> AgentOutput:
    if input.operation == 'add':
        answer = str(input.a + input.b)
        return AgentOutput(
            answer=answer,
            explanation=f'Adding {input.a} + {input.b} = {answer}',
            status='success',
        )
    if input.operation == 'multiply':
        answer = str(input.a * input.b)
        return AgentOutput(
            answer=answer,
            explanation=f'Multiplying {input.a} x {input.b} = {answer}',
            status='success',
        )
    return AgentOutput(
        answer='error',
        explanation='Unsupported operation',
        status='error',
    )


@app.post("/test", tags=["api"])
def test(data: dict) -> dict:
    return {"received": data}

@app.post("/api/score_prompt", tags=["api"])
def score_prompt(payload: dict, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Legacy endpoint for scoring prompts - creates a latte run."""
    prompt = payload.get("prompt", "")
    model = payload.get("model", "gpt-4o-mini")
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    try:
        # Create a latte run with defaults
        create_payload = LatteCreateRequest(
            system_prompt="You are a helpful AI assistant.",
            user_prompt=prompt,
            temperature=0.7,
            model=model,
            mock=None,  # Use default
        )
        run = create_latte_run(db, create_payload, settings=settings)
        return {
            "id": run.id,
            "score": run.score,
            "response": run.response,
            "note": run.baristas_note,
            "breakdown": run.scoring_breakdown,
        }
    except Exception:
        # Service unavailable (e.g., invalid API key, model not available)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@app.post("/api/run", tags=["api"])
def run_agent(agent_input: dict) -> dict:
    try:
        data = AgentInput(**agent_input)
        output = simulate_agent(data)
        objectives = evaluate_objectives(data, output)
        combined_pass = output.status == 'success' and all(obj.success for obj in objectives)
        record = RunRecord(
            id=generate_id(),
            input=data,
            output=output,
            objectives=objectives,
            combinedPass=combined_pass,
            latencyMs=random.randint(120, 260),
            startedAt=datetime.now(UTC).isoformat(),
        )
        return record.dict()
    except Exception as e:
        return {"error": str(e)}


class BenchmarkRunRequest(BaseModel):
    suite: str = "output"
    save: bool | None = True
    threshold: float | None = None


class ChatRequest(BaseModel):
    message: str


class LoginRequest(BaseModel):
    password: str


class AgentInput(BaseModel):
    operation: str
    a: int
    b: int


class AgentOutput(BaseModel):
    answer: str
    explanation: str
    status: str


class ObjectiveResult(BaseModel):
    id: str
    name: str
    kind: str
    success: bool
    details: str


class RunRecord(BaseModel):
    id: str
    input: AgentInput
    output: AgentOutput
    objectives: list[ObjectiveResult]
    combinedPass: bool
    latencyMs: int
    startedAt: str


@app.get("/benchmarks", tags=["benchmarks"], dependencies=[Depends(get_api_key)])
def get_benchmarks_snapshot() -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        snapshot = db.query(BenchmarkSnapshot).filter(BenchmarkSnapshot.suite == "output").first()
        if not snapshot or not snapshot.data.get("benchmarks"):
            payload = _generate_suite_payload("output")
            if snapshot:
                snapshot.data = payload
                snapshot.updated_at = datetime.now(UTC)
            else:
                snapshot = BenchmarkSnapshot(suite="output", data=payload)
                db.add(snapshot)
            db.commit()
        return snapshot.data["benchmarks"]
    finally:
        db.close()


@app.post("/benchmarks/run", tags=["benchmarks"], dependencies=[Depends(get_api_key)])
def run_benchmark_suite(request: BenchmarkRunRequest) -> dict[str, Any]:
    db = SessionLocal()
    try:
        suite = request.suite or "output"
        payload = _generate_suite_payload(suite, request.threshold)

        # Save snapshot
        snapshot = db.query(BenchmarkSnapshot).filter(BenchmarkSnapshot.suite == suite).first()
        if snapshot:
            snapshot.data = payload
            snapshot.updated_at = datetime.now(UTC)
        else:
            snapshot = BenchmarkSnapshot(suite=suite, data=payload)
            db.add(snapshot)

        # Save run
        summary = payload["summary"]
        run = BenchmarkRun(
            id=str(uuid4()),
            suite=suite,
            suite_label=SUITE_LABELS.get(suite, suite.title()),
            requested_at=datetime.now(UTC),
            generated_at=datetime.fromisoformat(payload["generatedAt"]),
            summary=summary,
            benchmark_count=summary["total"],
            failed=summary["failed"],
            success=summary["success"],
            status="success" if summary["failed"] == 0 else "needs_attention",
            threshold=request.threshold,
        )
        db.add(run)
        db.commit()
        return payload
    finally:
        db.close()


@app.post("/benchmarks/smoke", tags=["benchmarks"], dependencies=[Depends(get_api_key)])
def run_smoke_test() -> dict[str, Any]:
    db = SessionLocal()
    try:
        latency = round(random.uniform(0.25, 1.2), 3)
        output = "LLM mock smoke test passed."
        now = datetime.now(UTC)
        run = BenchmarkRun(
            id=str(uuid4()),
            suite="smoke",
            suite_label="LLM Smoke Test",
            requested_at=now,
            generated_at=now,
            summary={"total": 1, "success": 1, "failed": 0},
            benchmark_count=1,
            failed=0,
            success=1,
            status="success",
            threshold=None,
        )
        db.add(run)
        db.commit()
        return {"status": "ok", "latency": latency, "output": output}
    finally:
        db.close()


@app.get("/health/llm", tags=["benchmarks"], dependencies=[Depends(get_api_key)])
def llm_health() -> dict[str, Any]:
    latency = round(random.uniform(0.35, 1.5), 3)
    return {
        "status": "ok",
        "latency": latency,
        "model": settings.default_model,
        "output": "Mock LLM health ping succeeded.",
    }


@app.get("/runs", tags=["benchmarks"], dependencies=[Depends(get_api_key)])
def get_run_history() -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        runs = db.query(BenchmarkRun).order_by(BenchmarkRun.requested_at.desc()).limit(MAX_HISTORY).all()
        return [r.to_dict() for r in runs]
    finally:
        db.close()


@app.delete("/runs", tags=["benchmarks"], dependencies=[Depends(get_api_key)])
def clear_run_history() -> dict[str, str]:
    db = SessionLocal()
    try:
        db.query(BenchmarkRun).delete()
        db.commit()
        return {"message": "Run history cleared"}
    finally:
        db.close()


@app.get("/reliability_map", tags=["reliability"], dependencies=[Depends(get_api_key)])
def get_reliability_map() -> dict[str, Any]:
    """Mock reliability map data for visualization."""
    now = datetime.now(UTC)
    nodes = [
        {
            "id": "agent",
            "label": "Active Agent",
            "type": "agent",
            "score": round(random.uniform(0.7, 0.95), 2),
            "lastRun": (now - timedelta(minutes=random.randint(0, 60))).isoformat(),
        }
    ]
    links = []

    # Add suites from SUITE_TEMPLATES
    suite_ids = ["output", "custom", "crisis"]
    for suite_id in suite_ids:
        suite_label = SUITE_LABELS.get(suite_id, suite_id.title())
        score = round(random.uniform(0.6, 0.9), 2)
        nodes.append({
            "id": suite_id,
            "label": suite_label,
            "type": "suite",
            "score": score,
            "lastRun": (now - timedelta(minutes=random.randint(0, 120))).isoformat(),
        })
        strength = score
        drift = round(random.uniform(0.0, 0.3), 2)
        links.append({
            "source": "agent",
            "target": suite_id,
            "strength": strength,
            "drift": drift,
        })

    # Add personas
    personas = ["Rhema", "Tutor", "Analyst"]
    for persona in personas:
        score = round(random.uniform(0.65, 0.85), 2)
        nodes.append({
            "id": persona.lower(),
            "label": persona,
            "type": "persona",
            "score": score,
            "lastRun": (now - timedelta(minutes=random.randint(0, 90))).isoformat(),
        })
        strength = score
        drift = round(random.uniform(0.0, 0.25), 2)
        links.append({
            "source": "agent",
            "target": persona.lower(),
            "strength": strength,
            "drift": drift,
        })

    return {"nodes": nodes, "links": links}


@app.post("/chat", tags=["chat"], dependencies=[Depends(get_api_key)])
def chat_with_opencode(request: ChatRequest) -> dict[str, str]:
    if settings.mock_mode or not settings.openai_api_key:
        # Mock response - reversed text
        response = f"Opencode says: {request.message[::-1]}"
    else:
        # Use OpenAI as Opencode
        from langchain.schema import SystemMessage, HumanMessage
        llm = ChatOpenAI(
            model=settings.default_model,
            api_key=settings.openai_api_key,
            temperature=settings.temperature,
        )
        try:
            messages = [
                SystemMessage(content="You are Opencode, a helpful AI assistant specialized in software engineering, coding, and development tasks. Respond helpfully and technically, focusing on programming and engineering advice."),
                HumanMessage(content=request.message)
            ]
            ai_response = llm.invoke(messages)
            response = ai_response.content
        except Exception as e:
            response = f"Error: {str(e)}"
    return {"response": response}


@app.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    """Database health check endpoint."""
    try:
        # Simple query to test database connection
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {e}")
