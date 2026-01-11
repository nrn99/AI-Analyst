from pathlib import Path
import importlib.util

_ROOT = Path(__file__).resolve().parents[2]
_SOURCE = _ROOT / "finance-proxy" / "categories.py"


def _load_categories():
    if not _SOURCE.exists():
        raise RuntimeError(f"Missing categories source at {_SOURCE}")
    spec = importlib.util.spec_from_file_location("finance_proxy_categories", _SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load categories from {_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_categories()

UNCATEGORIZED = _module.UNCATEGORIZED
FIXED_CATEGORIES = _module.FIXED_CATEGORIES

__all__ = ["UNCATEGORIZED", "FIXED_CATEGORIES"]
