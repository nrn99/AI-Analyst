import logging
import os
import re
import sys
from datetime import datetime, timedelta

from env_utils import resolve_gcp_project_id
from backend.storers.sheets import SheetsLedgerStore

_MONTH_NAME_MAP = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
    "januari": 1,
    "februari": 2,
    "mars": 3,
    "april": 4,
    "maj": 5,
    "juni": 6,
    "juli": 7,
    "augusti": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}

_LIST_KEYWORDS = {
    "transactions",
    "transaction",
    "ledger",
    "statement",
    "history",
    "expenses",
    "expense",
    "movements",
    "movimenti",
    "transazioni",
    "spend",
    "spent",
    "balance",
}

UNCATEGORIZED = "Uncategorized"
FIXED_CATEGORIES = [
    "Income",
    "Housing",
    "Utilities",
    "Groceries",
    "Dining",
    "Transport",
    "Travel",
    "Shopping",
    "Subscriptions",
    "Health",
    "Education",
    "Business",
    "Taxes",
    "Fees",
    "Transfers",
    "Savings/Investments",
    UNCATEGORIZED,
]


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _parse_month_year(text: str):
    year = None
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        year = int(year_match.group(1))

    for name, month in _MONTH_NAME_MAP.items():
        if re.search(rf"\b{name}\b", text):
            return month, year
    return None, year


def _last_month():
    today = datetime.now().date()
    first = today.replace(day=1)
    prev = first - timedelta(days=1)
    return prev.month, prev.year


def _route_user_input(text: str):
    normalized = _normalize(text)
    if not normalized:
        return {"action": "clarify", "message": "Please enter a message."}

    if "uncategorized" in normalized or "uncategorised" in normalized or "needs review" in normalized:
        if "last month" in normalized or "previous month" in normalized or "forrige manad" in normalized:
            month, year = _last_month()
            return {"action": "uncategorized", "params": {"month": month, "year": year}}
        if "this month" in normalized or "current month" in normalized or "denna manad" in normalized:
            return {"action": "uncategorized", "params": {}}
        month, year = _parse_month_year(normalized)
        params = {}
        if month:
            params["month"] = month
        if year:
            params["year"] = year
        return {"action": "uncategorized", "params": params}

    if "last month" in normalized or "previous month" in normalized or "forrige manad" in normalized:
        month, year = _last_month()
        return {"action": "list", "params": {"month": month, "year": year}}

    if "this month" in normalized or "current month" in normalized or "denna manad" in normalized:
        return {"action": "list", "params": {}}

    if any(keyword in normalized for keyword in _LIST_KEYWORDS):
        month, year = _parse_month_year(normalized)
        params = {}
        if month:
            params["month"] = month
        if year:
            params["year"] = year
        return {"action": "list", "params": params}

    return {"action": "llm", "params": {}}


def _format_transactions(result: dict) -> str:
    month = result.get("month", "this month")
    transactions = result.get("transactions", [])
    if not transactions:
        return f"No transactions found for {month}."

    lines = [f"{t['date']} | {t['description']} | {t['category']} | {t['amount']}" for t in transactions]
    header = f"Transactions for {month} ({len(transactions)}):"
    return header + "\\n" + "\\n".join(lines)


def list_month_transactions(
    month: int | None = None,
    year: int | None = None,
    date: str | None = None,
    *,
    service=None,
    spreadsheet_id=None,
):
    """
    Fetch transactions for a specific month.
    Args:
        month: Month number (1-12). Defaults to current month when omitted.
        year: Year number. Defaults to current year when omitted.
        date: Optional anchor date (YYYY-MM-DD) to derive the month.
    Returns:
        Dict with month name, count, and transactions list.
    """
    store = SheetsLedgerStore(service=service, spreadsheet_id=spreadsheet_id)
    return store.list_transactions(month=month, year=year, date=date)


def list_uncategorized_transactions(
    month: int | None = None,
    year: int | None = None,
    date: str | None = None,
    *,
    service=None,
    spreadsheet_id=None,
):
    """
    Fetch transactions needing category review.
    """
    result = list_month_transactions(
        month=month,
        year=year,
        date=date,
        service=service,
        spreadsheet_id=spreadsheet_id,
    )
    transactions = []
    for transaction in result.get("transactions", []):
        category = _normalize(transaction.get("category", ""))
        if not category or category == _normalize(UNCATEGORIZED):
            transactions.append(transaction)
    result["transactions"] = transactions
    result["count"] = len(transactions)
    return result


def list_categories():
    """
    Return the fixed category list.
    """
    return {"categories": FIXED_CATEGORIES}


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
                Use available tools to read ledger data when asked about transactions.""",
            ),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        # Convert callables to tool objects
        try:
            def _build_tool(fn):
                if hasattr(Tool, "from_function"):
                    return Tool.from_function(
                        fn,
                        name=fn.__name__,
                        description=(fn.__doc__ or ""),
                    )
                return Tool(
                    fn,
                    name=fn.__name__,
                    description=(fn.__doc__ or ""),
                )

            tools = [
                _build_tool(list_month_transactions),
                _build_tool(list_uncategorized_transactions),
                _build_tool(list_categories),
            ]
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
        input_text = (input_text or "").strip()

        route = _route_user_input(input_text)
        if route.get("action") == "clarify":
            return route.get("message", "Please clarify your request.")
        if route.get("action") == "list":
            result = list_month_transactions(**route.get("params", {}))
            return _format_transactions(result)
        if route.get("action") == "uncategorized":
            result = list_uncategorized_transactions(**route.get("params", {}))
            return _format_transactions(result)

        if not self.executor:
            try:
                self.set_up()
            except Exception as exc:
                self._logger.error("Agent setup failed: %s", exc)
                return {"error": "agent_setup_failed", "detail": str(exc)}
        return self.executor.invoke({"input": input_text})["output"]
