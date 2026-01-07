import os

from scripts import startup_checks


def test_run_checks_returns_report_structure():
    # Ensure function runs and returns the expected keys
    report = startup_checks.run_checks(raise_on_error=False)
    assert isinstance(report, dict)
    assert "errors" in report and "warnings" in report
    assert isinstance(report["errors"], list)
    assert isinstance(report["warnings"], list)
