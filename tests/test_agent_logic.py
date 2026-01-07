import os
from datetime import datetime

import pytest

from agent_logic import get_localized_month_name, append_to_spreadsheet


class FakeValues:
    def __init__(self):
        self.updated = False
        self.appended = False

    def update(self, spreadsheetId=None, range=None, valueInputOption=None, body=None):
        self.updated = True
        return self

    def append(self, spreadsheetId=None, range=None, valueInputOption=None, body=None):
        self.appended = True
        return self

    def execute(self):
        return {"status": "ok"}


class FakeSpreadsheets:
    def __init__(self, locale="en_US", sheets=None):
        self._locale = locale
        self._sheets = sheets or [{"properties": {"title": "Existing"}}]
        self.batch_requested = False

    def get(self, spreadsheetId=None):
        class _Get:
            def __init__(self, locale, sheets):
                self._locale = locale
                self._sheets = sheets

            def execute(self):
                return {"properties": {"locale": self._locale}, "sheets": self._sheets}

        return _Get(self._locale, self._sheets)

    def batchUpdate(self, spreadsheetId=None, body=None):
        self.batch_requested = True
        class _Req:
            def execute(self_inner):
                return {"replies": []}
        return _Req()

    def values(self):
        return FakeValues()


class FakeService:
    def __init__(self, locale="en_US", sheets=None):
        self._spreadsheets = FakeSpreadsheets(locale=locale, sheets=sheets)

    def spreadsheets(self):
        return self._spreadsheets


def test_get_localized_month_name_sv():
    fake = FakeService(locale="sv_SE")
    name = get_localized_month_name(fake, spreadsheet_id="dummy")
    # Expect Swedish month for current month
    swedish = ["Januari", "Februari", "Mars", "April", "Maj", "Juni", "Juli", "Augusti", "September", "Oktober", "November", "December"]
    assert name == swedish[datetime.now().month - 1]


def test_get_localized_month_name_it():
    fake = FakeService(locale="it_IT")
    name = get_localized_month_name(fake, spreadsheet_id="dummy")
    italian = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    assert name == italian[datetime.now().month - 1]


def test_append_to_spreadsheet_creates_tab_and_appends():
    # create fake service with no matching month tab so code will create the tab
    # use a unique month name by forcing locale to english but removing existing month
    fake = FakeService(locale="en_US", sheets=[{"properties": {"title": "Other"}}])

    # call function with injected service and spreadsheet id to avoid env reliance
    res = append_to_spreadsheet(10.0, "Test", "Misc", service=fake, spreadsheet_id="sheet123")
    assert "Success: Logged to" in res
