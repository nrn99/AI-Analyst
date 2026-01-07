import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import vertexai
from vertexai.preview import reasoning_engines

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


def require_api_key(x_api_key: str = Header(None, alias="X-Api-Key")):
    expected = _clean_env(os.getenv("LOVABLE_PROXY_KEY"))
    if not expected:
        raise HTTPException(status_code=500, detail="Server misconfigured: LOVABLE_PROXY_KEY not set")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


def _extract_reply(result):
    if isinstance(result, dict):
        for key in ("output", "response", "reply", "text"):
            if key in result:
                return str(result[key])
        return str(result)
    return str(result)


app = FastAPI(title="Lovable Vertex AI Proxy", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    status = "ok" if REMOTE_AGENT and not INIT_ERROR else "degraded"
    detail = "ready" if status == "ok" else "init_failed"
    return {"status": status, "detail": detail}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
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


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
