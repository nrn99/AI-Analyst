import logging
import os
import sys

from env_utils import resolve_gcp_project_id
from backend.storers.sheets import SheetsLedgerStore

def append_to_spreadsheet(
    amount: float,
    description: str,
    category: str = "Misc",
    date: str | None = None,
    *,
    service=None,
    spreadsheet_id=None,
):
    """
    Logs a transaction to the finance ledger.
    Args:
        amount: The numerical value (use negative for expenses).
        description: A short note about the transaction.
        category: The budget category (e.g., Food, Travel).
        date: Optional transaction date (YYYY-MM-DD).
    """
    store = SheetsLedgerStore(service=service, spreadsheet_id=spreadsheet_id)
    result = store.append_transaction(
        amount=amount,
        description=description,
        category=category,
        date=date,
    )
    return result.get("message", "Logged")


# 3. The Agent Class
class FinanceAnalystAgent:
    def __init__(self):
        self.executor = None
        self._last_setup_error = None
        self._logger = logging.getLogger("backend.processors.FinanceAnalystAgent")
        if not logging.getLogger().handlers:
            # Basic logging config for local runs/tests
            logging.basicConfig(level=logging.INFO)

    def set_up(self):
        # Validate critical env vars early
        project = resolve_gcp_project_id(set_env=True)
        if not project:
            raise RuntimeError(
                "GCP_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) is not set and project auto-detection failed"
            )

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.tools import Tool
        except Exception as exc:
            msg = f"LangChain-related dependencies missing or incompatible: {exc}"
            self._logger.exception(msg)
            raise RuntimeError(msg) from exc

        # Log versions to help debugging in deployments
        try:
            import importlib.metadata as _m
            versions = {"python": sys.version.splitlines()[0]}
            for pkg in (
                "langchain",
                "langchain_core",
                "langchain_classic",
                "langchain_google_genai",
            ):
                try:
                    versions[pkg] = _m.version(pkg)
                except Exception:
                    versions[pkg] = None
            self._logger.info("Dependency versions: %s", versions)
        except Exception:
            pass

        # Explicit Vertex AI Config
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=0,
                vertexai=True,
                project=project,
                location=os.getenv("GCP_LOCATION", "europe-west1"),
            )
        except Exception as exc:
            msg = f"Failed to initialize LLM: {exc}"
            self._logger.exception(msg)
            raise RuntimeError(msg) from exc

        # System instructions that handle all your languages
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a multilingual Personal Finance Assistant.
                You can understand Swedish, Italian, and English.
                Always log expenses as negative numbers.
                If a category isn't clear, use your best judgment or ask for clarification.""",
            ),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        # Convert callables to tool objects
        try:
            if hasattr(Tool, "from_function"):
                tool_obj = Tool.from_function(
                    append_to_spreadsheet,
                    name=append_to_spreadsheet.__name__,
                    description=(append_to_spreadsheet.__doc__ or ""),
                )
            else:
                tool_obj = Tool(
                    append_to_spreadsheet,
                    name=append_to_spreadsheet.__name__,
                    description=(append_to_spreadsheet.__doc__ or ""),
                )
            tools = [tool_obj]
            self._logger.info("Prepared tools: %s", [getattr(t, "name", str(t)) for t in tools])
        except Exception as exc:
            msg = f"Failed to prepare tools: {exc}"
            self._logger.exception(msg)
            raise RuntimeError(msg) from exc

        # Create agent and executor robustly, surface clear errors
        try:
            agent = create_tool_calling_agent(llm, tools, prompt)
            self.executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
            self._last_setup_error = None
        except Exception as exc:
            self.executor = None
            self._last_setup_error = exc
            msg = (
                "Failed to initialize AgentExecutor. Possible causes: mismatched langchain versions, "
                "incorrect tool objects (functions vs Tool instances), or invalid prompt/LLM initialization. "
                f"Original error: {exc}"
            )
            self._logger.exception(msg)
            raise RuntimeError(msg) from exc

    def query(self, input_text: str | None = None, input: str | None = None, **_kwargs):
        if input_text is None:
            input_text = input
        if not self.executor:
            try:
                self.set_up()
            except Exception as exc:
                self._logger.error("Agent setup failed: %s", exc)
                return {"error": "agent_setup_failed", "detail": str(exc)}
        return self.executor.invoke({"input": input_text})["output"]
