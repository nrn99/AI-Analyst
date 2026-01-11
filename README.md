# AI Analyst Backend

Backend logic for the personal finance ledger and AI analysis.

## Architecture

- Fetchers: parse uploaded statements (drag-and-drop)
- Processors: AI agent and categorization/RAG logic
- Storers: append-only ledger storage in Google Sheets with idempotency checks

## Key modules

- backend/storers/sheets.py
- backend/processors/agent.py
- finance-proxy/ (Lovable-facing proxy API)

## Environment

- GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT
- GCP_LOCATION
- LEDGER_SPREADSHEET_ID
- GOOGLE_APPLICATION_CREDENTIALS (local dev only; Cloud Run uses ADC)
- STAGING_BUCKET (deploy only)

## Idempotency

Sheet writes are "check, then append" based on Date + Amount + Description.
Corrections should be new rows, not edits.

## Deploy

Run the Reasoning Engine deployment script, then update the proxy env file with the new resource name, and deploy the proxy to Cloud Run.

```bash
# Deploy / update the Reasoning Engine (from repo root)
python scripts/deploy_reasoning_engine.py

# Update finance-proxy/env.yaml with the latest REASONING_ENGINE_RESOURCE output

# Deploy the proxy to Cloud Run
gcloud run deploy finance-bridge \
  --source finance-proxy \
  --env-vars-file finance-proxy/env.yaml \
  --region europe-west1 \
  --allow-unauthenticated
```
