import logging
import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAULT_HEADERS = ["Datum", "Beskrivning", "Kategori", "Belopp"]

_MONTH_MAPS = {
    "sv": [
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
    ],
    "it": [
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
    ],
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
)


def _normalize_text(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).lower()


def _parse_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _normalize_date(value):
    parsed = _parse_date(value)
    if parsed:
        return parsed.date().isoformat()
    if value is None:
        return ""
    return str(value).strip()


def _normalize_amount(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    s = str(value).strip()
    if not s:
        return None
    s = s.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _amounts_match(left, right):
    left_norm = _normalize_amount(left)
    right_norm = _normalize_amount(right)
    if left_norm is not None and right_norm is not None:
        return left_norm == right_norm
    return _normalize_text(left) == _normalize_text(right)


def _row_is_header(row):
    if len(row) < 4:
        return False
    return [_normalize_text(cell) for cell in row[:4]] == [
        _normalize_text(cell) for cell in DEFAULT_HEADERS
    ]


def _localized_month_name(locale, when=None):
    lang_code = locale.split("_")[0].lower() if locale else "en"
    month_list = _MONTH_MAPS.get(lang_code, _MONTH_MAPS["en"])
    stamp = _parse_date(when) or datetime.now()
    return month_list[stamp.month - 1]


def get_localized_month_name(service, spreadsheet_id, when=None, locale=None):
    if locale is None:
        res = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        locale = res.get("properties", {}).get("locale", "en_US")
    return _localized_month_name(locale, when)


class SheetsLedgerStore:
    def __init__(self, service=None, spreadsheet_id=None):
        self._service = service
        self._spreadsheet_id = spreadsheet_id
        self._logger = logging.getLogger("backend.storers.sheets")

    def _ensure_service(self):
        if self._service is not None:
            return self._service
        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
        except Exception as exc:
            raise RuntimeError(
                "googleapiclient and google.oauth2 are required when no service is passed"
            ) from exc

        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not key_path:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not set")
        creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
        self._service = build("sheets", "v4", credentials=creds)
        return self._service

    def _ensure_spreadsheet_id(self):
        if not self._spreadsheet_id:
            self._spreadsheet_id = os.getenv("LEDGER_SPREADSHEET_ID")
        if not self._spreadsheet_id:
            raise RuntimeError("LEDGER_SPREADSHEET_ID is not set")
        return self._spreadsheet_id

    def _ensure_month_sheet(self, service, spreadsheet_id, month_name, sheet_names):
        if month_name in sheet_names:
            return False
        batch_update = {"requests": [{"addSheet": {"properties": {"title": month_name}}}]}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=batch_update,
        ).execute()

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{month_name}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [DEFAULT_HEADERS]},
        ).execute()
        return True

    def is_duplicate(self, date_value, amount, description, sheet_name):
        service = self._ensure_service()
        spreadsheet_id = self._ensure_spreadsheet_id()

        values = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A:D",
            )
            .execute()
            .get("values", [])
        )

        start_index = 1 if values and _row_is_header(values[0]) else 0
        target_date = _normalize_date(date_value)
        target_desc = _normalize_text(description)

        for row in values[start_index:]:
            row_date = _normalize_date(row[0]) if len(row) > 0 else ""
            row_desc = _normalize_text(row[1]) if len(row) > 1 else ""
            row_amount = row[3] if len(row) > 3 else ""
            if (
                row_date == target_date
                and row_desc == target_desc
                and _amounts_match(row_amount, amount)
            ):
                return True
        return False

    def append_transaction(self, amount, description, category="Misc", date=None):
        service = self._ensure_service()
        spreadsheet_id = self._ensure_spreadsheet_id()

        description = (description or "").strip() or "Unknown"
        category = (category or "").strip() or "Uncategorized"
        date_value = _normalize_date(date) or datetime.now().strftime("%Y-%m-%d")

        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        locale = spreadsheet.get("properties", {}).get("locale", "en_US")
        sheet_names = [
            sheet.get("properties", {}).get("title", "")
            for sheet in spreadsheet.get("sheets", [])
        ]

        month_name = get_localized_month_name(
            service,
            spreadsheet_id,
            when=date_value,
            locale=locale,
        )

        created = self._ensure_month_sheet(
            service,
            spreadsheet_id,
            month_name,
            sheet_names,
        )
        if not created and self.is_duplicate(date_value, amount, description, month_name):
            self._logger.info(
                "Duplicate skipped: %s %s %s", date_value, amount, description
            )
            return {"status": "duplicate", "message": f"Duplicate skipped in '{month_name}' tab."}

        row = [date_value, description, category, amount]
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{month_name}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        ).execute()

        self._logger.info("Ledger appended: %s %s %s", date_value, amount, description)
        return {"status": "appended", "message": f"Success: Logged to '{month_name}' tab."}
