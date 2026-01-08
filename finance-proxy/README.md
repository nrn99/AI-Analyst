# Lovable -> Vertex AI Proxy

FastAPI service that proxies Lovable.dev requests to a Vertex AI Reasoning Engine.

## Configure

Create a `.env` file (see `.env.example`) or set environment variables:

- `LOVABLE_PROXY_KEY` - shared secret for `X-Api-Key`
- `GCP_PROJECT_ID` - GCP project id (default: `nestaai`)
- `GCP_LOCATION` - Vertex region (default: `europe-west1`)
- `REASONING_ENGINE_RESOURCE` - full resource name of the Reasoning Engine
- `GOOGLE_APPLICATION_CREDENTIALS` - service account JSON path (Sheets access)
- `LEDGER_SPREADSHEET_ID` - target ledger sheet ID
- `CATEGORY_SUGGESTION_MODE` - `model` (default) or `heuristic`

For local auth, use ADC:

```bash
gcloud auth application-default login
```

## Setup (uv)

```bash
uv init
uv add fastapi uvicorn google-cloud-aiplatform[agent_engines] python-dotenv python-multipart openpyxl pypdf google-api-python-client google-auth google-auth-httplib2
```

Generate a key:

```bash
python3 -c "import secrets; print(f'LOVABLE_PROXY_KEY={secrets.token_urlsafe(32)}')" >> .env
```

Add your project id:

```bash
echo "GCP_PROJECT_ID=nestaai" >> .env
```

## Run locally

```bash
uv run python main.py
```

## Cloud Run deploy

```bash
gcloud run deploy finance-bridge \
  --source . \
  --env-vars-file .env \
  --region europe-west1 \
  --allow-unauthenticated
```

## API

`POST /chat`

Request body:

```json
{"message": "user input string"}
```

Response body:

```json
{"reply": "AI response string"}
```

`POST /ingest/preview` (multipart form-data)

Response body includes `transactions` with `category_suggested` and `needs_review`.

`POST /ingest/commit`

Request body:

```json
{"transactions": [{"date":"2024-08-01","description":"Coffee","amount":-4.5,"category_approved":"Dining"}]}
```

`GET /categories`

Returns the fixed categories list for UI review flows.
