from pathlib import Path
import importlib.util

_ROOT = Path(__file__).resolve().parents[2]
_LEDGER_PATH = _ROOT / "finance-proxy" / "ledger.py"


def _load_ledger():
    if not _LEDGER_PATH.exists():
        raise RuntimeError(f"Missing ledger source at {_LEDGER_PATH}")
    spec = importlib.util.spec_from_file_location("finance_proxy_ledger", _LEDGER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ledger module from {_LEDGER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ledger = _load_ledger()

DEFAULT_HEADERS = _ledger.DEFAULT_HEADERS
get_localized_month_name = _ledger.get_localized_month_name
SheetsLedgerStore = _ledger.SheetsLedgerStore

__all__ = ["DEFAULT_HEADERS", "get_localized_month_name", "SheetsLedgerStore"]
