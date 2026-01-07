Purpose
-------
This file guides AI coding agents (Copilot-like) to become productive in this repository quickly. It focuses on discoverable, actionable knowledge: high-level architecture, developer workflows, conventions, integration points, and exact commands to run while exploring the project.

How to use this file
--------------------
- Start by running the discovery commands listed below to populate missing details.
- If you (human) know concrete build/test commands or key file paths, paste them into the "Project-specific facts" section.

Quick discovery commands
------------------------
Run these from the repo root to discover architecture and workflows:

```
git status --porcelain --untracked-files=no
ls -la
rg "^name|scripts|main|entry|app|server|cli" --hidden || true
rg "Dockerfile|docker-compose.yml|Makefile|pyproject.toml|package.json|requirements.txt|Pipfile" --hidden || true
cat README.md 2>/dev/null || true
```

Project-specific facts (fill in)
--------------------------------
- Primary language: (e.g. JavaScript/TypeScript / Python / Go)
- Build command: (e.g. `npm run build`, `python -m build`, `go build ./...`)
- Test command: (e.g. `npm test`, `pytest`, `go test ./...`)
- Dev server / run command: (e.g. `npm start`, `uvicorn app.main:app --reload`)
- CI: (CI provider and notable workflows under `.github/workflows`)
- Key entry files / directories: (e.g. `src/`, `cmd/`, `app/`, `main.py`)
- Any generated folders to ignore: (e.g. `dist/`, `build/`, `.venv/`)

Big-picture architecture (how to discover)
-----------------------------------------
- Look for the service entrypoints named in `package.json` / `pyproject.toml` / `cmd/`.
- If a `Dockerfile` or `docker-compose.yml` exists then components are likely containerized; inspect exposed ports and healthchecks there.
- For multi-service setups, check top-level directories for names like `api/`, `worker/`, `frontend/` and open their README or `Dockerfile` to learn responsibilities.

Conventions and patterns to look for
-----------------------------------
- Script-based workflows: prefer `npm run <task>` or `make <target>` when present; use those rather than ad-hoc commands.
- Configuration: prefer environment variables documented in `README.md` or `.env.example`. If neither exists, search for `os.getenv`, `process.env`, or `dotenv` usage.
- Database and migrations: look for `migrations/`, `alembic/`, `prisma/`, or `knexfile.js` to understand schema lifecycle.

Integration points and secrets
-----------------------------
- Check for `secrets` / `env` references in CI workflows under `.github/workflows`.
- External services: search for clients like `boto3`, `aws-sdk`, `pg`, `redis`, `httpx`, `axios` to find integrations.

Editing and PR guidance for AI agents
------------------------------------
- Keep changes minimal and focused to the task. Avoid broad refactors unless requested.
- Preserve existing file and folder structure; do not rename or delete top-level folders.
- When adding commands or modifying build steps, update `README.md` and add a short note in the PR description explaining the reasoning.

If this repo already contains agent guidance
------------------------------------------
- If a pre-existing agent doc is present (e.g., AGENT.md, copilot-instructions.md), merge its factual sections into the "Project-specific facts" above rather than duplicating high-level advice.

Missing information checklist for humans
--------------------------------------
- Please fill the "Project-specific facts" block with concrete commands and paths.
- Add links to any infra diagrams, ADRs, or architecture docs if available.

Follow-up
--------
After you fill in the facts above, ask the agent to regenerate this file to inline concrete examples (commands, entry files, CI links) so future agents have fewer discovery steps.
