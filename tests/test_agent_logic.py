from datetime import datetime

from backend.processors.agent import list_uncategorized_transactions
from backend.storers.sheets import DEFAULT_HEADERS, SheetsLedgerStore, get_localized_month_name


class FakeValues:
    def __init__(self, initial_values=None):
        self.updated = False
        self.appended = False
        self._values = list(initial_values or [])

    def get(self, spreadsheetId=None, range=None):
        class _Get:
            def __init__(self, values):
                self._values = values

            def execute(self):
                return {"values": self._values}

        return _Get(self._values)

    def update(self, spreadsheetId=None, range=None, valueInputOption=None, body=None):
        self.updated = True
        if body and "values" in body:
            self._values = body["values"] + self._values
        return self

    def append(self, spreadsheetId=None, range=None, valueInputOption=None, body=None):
        self.appended = True
        if body and "values" in body:
            self._values.extend(body["values"])
        return self

    def execute(self):
        return {"status": "ok"}


class FakeSpreadsheets:
    def __init__(self, locale="en_US", sheets=None, values=None):
        self._locale = locale
        self._sheets = sheets or [{"properties": {"title": "Existing"}}]
        self._values = FakeValues(values)
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
        return self._values


class FakeService:
    def __init__(self, locale="en_US", sheets=None, values=None):
        self._spreadsheets = FakeSpreadsheets(locale=locale, sheets=sheets, values=values)

    def spreadsheets(self):
        return self._spreadsheets


def test_get_localized_month_name_sv():
    fake = FakeService(locale="sv_SE")
    name = get_localized_month_name(fake, spreadsheet_id="dummy")
    swedish = [
        "Januari",
        "Februari",
        "Mars",
        "April",
        "Maj",
        "Juni",
        "Juli",
        "Augusti",
        "September",
        "Oktober",
        "November",
        "December",
    ]
    assert name == swedish[datetime.now().month - 1]


def test_get_localized_month_name_it():
    fake = FakeService(locale="it_IT")
    name = get_localized_month_name(fake, spreadsheet_id="dummy")
    italian = [
        "Gennaio",
        "Febbraio",
        "Marzo",
        "Aprile",
        "Maggio",
        "Giugno",
        "Luglio",
        "Agosto",
        "Settembre",
        "Ottobre",
        "Novembre",
        "Dicembre",
    ]
    assert name == italian[datetime.now().month - 1]


def test_ledger_append_creates_tab_and_appends():
    fake = FakeService(locale="en_US", sheets=[{"properties": {"title": "Other"}}])
    store = SheetsLedgerStore(service=fake, spreadsheet_id="sheet123")
    res = store.append_transaction(10.0, "Test", "Misc", date="2026-01-06")

    assert res["status"] == "appended"
    assert fake._spreadsheets.batch_requested is True
    assert fake._spreadsheets.values().updated is True
    assert fake._spreadsheets.values().appended is True


def test_ledger_append_skips_duplicate():
    month_name = get_localized_month_name(
        FakeService(locale="en_US"),
        spreadsheet_id="sheet123",
        when="2026-01-06",
    )
    values = [
        DEFAULT_HEADERS,
        ["2026-01-06", "Test", "Misc", "10.0"],
    ]
    fake = FakeService(
        locale="en_US",
        sheets=[{"properties": {"title": month_name}}],
        values=values,
    )
    store = SheetsLedgerStore(service=fake, spreadsheet_id="sheet123")
    res = store.append_transaction(10.0, "Test", "Misc", date="2026-01-06")

    assert res["status"] == "duplicate"
    assert fake._spreadsheets.values().appended is False


def test_list_transactions_returns_month_rows():
    month_name = get_localized_month_name(
        FakeService(locale="en_US"),
        spreadsheet_id="sheet123",
        when="2026-01-06",
    )
    values = [
        DEFAULT_HEADERS,
        ["2026-01-06", "Coffee", "Food", "5.00"],
        ["2026-01-07", "Bus", "Travel", "-2.50"],
    ]
    fake = FakeService(
        locale="en_US",
        sheets=[{"properties": {"title": month_name}}],
        values=values,
    )
    store = SheetsLedgerStore(service=fake, spreadsheet_id="sheet123")
    res = store.list_transactions(date="2026-01-06")

    assert res["month"] == month_name
    assert res["count"] == 2
    assert res["transactions"][0]["description"] == "Coffee"


def test_list_uncategorized_transactions_filters_rows():
    month_name = get_localized_month_name(
        FakeService(locale="en_US"),
        spreadsheet_id="sheet123",
        when="2026-01-06",
    )
    values = [
        DEFAULT_HEADERS,
        ["2026-01-06", "Coffee", "Uncategorized", "5.00"],
        ["2026-01-07", "Bus", "Travel", "-2.50"],
    ]
    fake = FakeService(
        locale="en_US",
        sheets=[{"properties": {"title": month_name}}],
        values=values,
    )
    res = list_uncategorized_transactions(
        service=fake,
        spreadsheet_id="sheet123",
        date="2026-01-06",
    )

    assert res["count"] == 1
    assert res["transactions"][0]["description"] == "Coffee"
