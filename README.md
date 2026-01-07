# Vertex AI Agent Flask Backend

Simple Flask backend that demonstrates a minimal integration with Vertex AI Generative Model (`gemini-1.5-flash`). Includes a tiny frontend served from `templates/index.html`.

## Files
- [app.py](app.py) - Flask app with `/`, `/health`, and `/chat` endpoints
- [templates/index.html](templates/index.html) - Minimal UI with buttons to call the backend
- [requirements.txt](requirements.txt) - Python deps

## Requirements
- Python 3.8+
- A Google Cloud project with Vertex AI enabled (for real model calls)
- Service account JSON key (if running locally)

## Install (using uv)

Install `uv` (choose one):

```bash
# standalone installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# or with pipx
pipx install uv

# or Homebrew on macOS
brew install uv
```

Create the project virtual environment and install dependencies:

```bash
cd /path/to/project
uv venv            # creates .venv (asks if none found)
uv pip install -r requirements.txt
```

## Environment
Set these before running (example):

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
export AI_PLATFORM_LOCATION=europe-north1
```

If you don't set `GOOGLE_CLOUD_PROJECT` or credentials, the `/chat` endpoint will return a fallback message.

## Run

Start the app inside the project environment:

```bash
uv run python app.py
```

Open http://localhost:8080/ to view the frontend.

## Endpoints
- `GET /health` — returns `{"status":"healthy"}`
- `POST /chat` — invokes Vertex AI (`gemini-1.5-flash`) and returns JSON `{"response": "..."}`; on error returns a fallback response and an `error` field.

## Notes
- Ensure Vertex AI API is enabled in the project and the service account has appropriate permissions for Vertex AI.
- The `app.py` uses `google-cloud-aiplatform` and attempts to initialize with `aiplatform.init()` if `GOOGLE_CLOUD_PROJECT` is set.

### Unsupported region mitigation

- If you see a ValueError like "Unsupported region for Vertex AI", it means the region you set in `AI_PLATFORM_LOCATION` is not recognized by the client library for Vertex AI. Common causes and mitigations:
	- **Typo or quoting**: Ensure `AI_PLATFORM_LOCATION` contains a raw region string (e.g. `europe-north1`) with no surrounding quotes. The project includes logic to strip surrounding quotes, but it's best to keep it unquoted in `.env`.
	- **Unsupported region**: Choose a supported region from the error message (for Stockholm vicinity prefer `europe-north1` or `europe-west3`). The app will automatically fall back to `europe-north1` if initialization fails due to an unsupported region.
	- **Outdated client library**: Upgrade the client library to the latest version:

```bash
uv pip install --upgrade google-cloud-aiplatform
```

After changing `AI_PLATFORM_LOCATION` or upgrading the library, restart the app (use `uv run python app.py`).
