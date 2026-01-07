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
- GOOGLE_APPLICATION_CREDENTIALS
- LEDGER_SPREADSHEET_ID
- STAGING_BUCKET (deploy only)

## Idempotency

Sheet writes are "check, then append" based on Date + Amount + Description.
Corrections should be new rows, not edits.
