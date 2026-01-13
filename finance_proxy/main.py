import logging
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import vertexai
from vertexai.preview import reasoning_engines

from core.categories import FIXED_CATEGORIES, UNCATEGORIZED
from core.ingest import parse_statement
from core.ledger import SheetsLedgerStore

load_dotenv()

def _clean_env(value):
    if not value:
        return None
    cleaned = value.strip().strip("'\"")
    return cleaned or None


PROJECT_ID = _clean_env(
    os.getenv("GCP_PROJECT_ID")
    or os.getenv("GOOGLE_CLOUD_PROJECT")
    or "nestaai"
)
LOCATION = _clean_env(os.getenv("GCP_LOCATION")) or "europe-west1"
REASONING_ENGINE_RESOURCE = _clean_env(
    os.getenv("REASONING_ENGINE_RESOURCE")
    or "projects/326216802468/locations/europe-west1/reasoningEngines/2800588057340805120"
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("finance_proxy")


def _init_reasoning_engine():
    if not PROJECT_ID:
        raise RuntimeError("GCP_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) is not set")
    if not REASONING_ENGINE_RESOURCE:
        raise RuntimeError("REASONING_ENGINE_RESOURCE is not set")

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    try:
        return reasoning_engines.ReasoningEngine(resource_name=REASONING_ENGINE_RESOURCE)
    except TypeError:
        pass

    try:
        if hasattr(reasoning_engines.ReasoningEngine, "from_resource_name"):
            return reasoning_engines.ReasoningEngine.from_resource_name(REASONING_ENGINE_RESOURCE)
    except Exception:
        pass

    return reasoning_engines.ReasoningEngine(REASONING_ENGINE_RESOURCE)


REMOTE_AGENT = None
INIT_ERROR = None
try:
    REMOTE_AGENT = _init_reasoning_engine()
    LOGGER.info("Loaded Reasoning Engine: %s", REASONING_ENGINE_RESOURCE)
except Exception as exc:
    INIT_ERROR = exc
    LOGGER.exception("Failed to initialize Reasoning Engine: %s", exc)





class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class TransactionApproval(BaseModel):
    date: str
    description: str
    amount: float
    category_approved: str | None = None
    category_suggested: str | None = None


class CommitRequest(BaseModel):
    transactions: list[TransactionApproval] = Field(default_factory=list)


def _extract_reply(result):
    if isinstance(result, dict):
        for key in ("output", "response", "reply", "text"):
            if key in result:
                return str(result[key])
        return str(result)
    return str(result)


def _normalize_category(value):
    if not value:
        return UNCATEGORIZED
    raw = str(value).strip()
    for category in FIXED_CATEGORIES:
        if raw.lower() == category.lower():
            return category
    return UNCATEGORIZED


_AUDIT_EXCLUDE = {"internal", "transfer", "transfers"}
_AUDIT_INCOME = {"external income", "income"}
_AUDIT_MACHINE = {"rent", "food", "transport", "insurance", "medical", "tithe"}
_AUDIT_FLOW = {"gym", "hair", "dining", "hobbies"}
_AUDIT_SOVEREIGNTY = {"savings", "investment", "investments", "savings/investments"}


def _normalize_label(value):
    return " ".join(str(value or "").strip().lower().split())


def _parse_amount(value):
    if value is None:
        return Decimal("0")
    raw = str(value).strip()
    if not raw:
        return Decimal("0")
    raw = raw.replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(",", "")
    else:
        raw = raw.replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0")


def _as_amount(value):
    return float(value.quantize(Decimal("0.01")))


def _as_percentage(total, income):
    if income <= 0:
        return 0.0
    return float((total / income).quantize(Decimal("0.0001")))


app = FastAPI(title="Lovable Vertex AI Proxy", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    LOGGER.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        LOGGER.info(f"Response: {response.status_code}")
        return response
    except Exception as e:
        LOGGER.error(f"Request failed: {e}")
        raise


@app.get("/health")
def health():
    status = "ok" if REMOTE_AGENT and not INIT_ERROR else "degraded"
    detail = "ready" if status == "ok" else "init_failed"
    return {"status": status, "detail": detail}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    if INIT_ERROR or not REMOTE_AGENT:
        raise HTTPException(status_code=500, detail="Reasoning engine not initialized")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = REMOTE_AGENT.query(input=message)
    except Exception as exc:
        LOGGER.exception("Reasoning engine query failed: %s", exc)
        raise HTTPException(status_code=500, detail="Reasoning engine query failed")

    return {"reply": _extract_reply(result)}


@app.get("/categories")
def list_categories():
    return {"categories": FIXED_CATEGORIES}


@app.get("/audit/summary")
def audit_summary():
    try:
        store = SheetsLedgerStore()
        result = store.list_transactions()
    except Exception as exc:
        LOGGER.exception("Failed to fetch ledger data: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch ledger data")

    transactions = result.get("transactions", [])
    if not transactions:
        return {
            "income": 0,
            "machine": {"total": 0, "percentage": 0, "status": "No Data"},
            "flow": {"total": 0, "percentage": 0, "status": "No Data"},
            "sovereignty": {"total": 0, "percentage": 0, "status": "No Data"},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    income_total = Decimal("0")
    machine_total = Decimal("0")
    flow_spend = Decimal("0")
    sovereignty_total = Decimal("0")
    tithe_total = Decimal("0")

    for entry in transactions:
        category = _normalize_label(entry.get("category", ""))
        if not category or category in _AUDIT_EXCLUDE:
            continue
        amount = _parse_amount(entry.get("amount"))
        if amount == 0:
            continue
        amount = abs(amount)

        if category in _AUDIT_INCOME:
            income_total += amount
        if category in _AUDIT_MACHINE:
            machine_total += amount
            if category == "tithe":
                tithe_total += amount
        if category in _AUDIT_FLOW:
            flow_spend += amount
        if category in _AUDIT_SOVEREIGNTY:
            sovereignty_total += amount

    flow_target = income_total * Decimal("0.30")
    flow_unspent = flow_target - flow_spend
    if flow_unspent < 0:
        flow_unspent = Decimal("0")
    flow_total = flow_spend + flow_unspent

    if income_total <= 0:
        machine_status = "No Data"
        flow_status = "No Data"
    else:
        machine_status = "Antifragile" if machine_total <= income_total * Decimal("0.50") else "Fragile"
        flow_status = "Disciplined" if flow_total <= income_total * Decimal("0.30") else "Undisciplined"

    sovereignty_status = (
        "Steward" if tithe_total > 0 and sovereignty_total > 0 else "Needs Stewardship"
    )
    if income_total <= 0:
        sovereignty_status = "No Data"

    return {
        "income": _as_amount(income_total),
        "machine": {
            "total": _as_amount(machine_total),
            "percentage": _as_percentage(machine_total, income_total),
            "status": machine_status,
        },
        "flow": {
            "total": _as_amount(flow_total),
            "percentage": _as_percentage(flow_total, income_total),
            "status": flow_status,
        },
        "sovereignty": {
            "total": _as_amount(sovereignty_total),
            "percentage": _as_percentage(sovereignty_total, income_total),
            "status": sovereignty_status,
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/ingest/preview")
async def ingest_preview(
    file: UploadFile = File(...),
    limit: int = Query(500, ge=1, le=5000),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = parse_statement(
            data=data,
            filename=file.filename or "",
            content_type=file.content_type or "",
            project_id=PROJECT_ID,
            location=LOCATION,
        )
    except Exception as exc:
        LOGGER.exception("Failed to parse statement: %s", exc)
        raise HTTPException(status_code=400, detail="Failed to parse statement file")

    transactions = result.get("transactions", [])
    truncated = False
    if limit and len(transactions) > limit:
        result["transactions"] = transactions[:limit]
        truncated = True

    result["truncated"] = truncated
    result["needs_review_count"] = sum(1 for t in result.get("transactions", []) if t.get("needs_review"))
    result["total_transactions"] = len(transactions)
    return result


@app.post("/ingest/commit")
async def ingest_commit(payload: CommitRequest):
    if not payload.transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    normalized = []
    for item in payload.transactions:
        category = _normalize_category(item.category_approved or item.category_suggested)
        normalized.append(
            {
                "date": item.date,
                "description": item.description,
                "amount": item.amount,
                "category": category,
            }
        )

    try:
        store = SheetsLedgerStore()
        result = store.append_transactions(normalized)
    except Exception as exc:
        LOGGER.exception("Commit failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to write transactions to ledger")

    return {
        "appended": result.get("appended", 0),
        "duplicates": result.get("duplicates", 0),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
