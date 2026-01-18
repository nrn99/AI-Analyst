import logging
import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import google.auth
from googleapiclient.discovery import build
from .categories import MACHINE_PILLARS, INTEGRITY_FILTERS, ROOT_TRIGGERS

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAULT_HEADERS = [
    "Date",
    "Description",
    "Amount",
    "Category",
    "Machine Pillar",
    "Integrity Filter",
    "Root Trigger",
    "Notes",
]

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
    return " ".join(str(value).strip().split())


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
    return _normalize_text(left).lower() == _normalize_text(right).lower()


def _row_is_header(row):
    if len(row) < 8:
        return False
    return [_normalize_text(cell).lower() for cell in row[:8]] == [
        _normalize_text(cell).lower() for cell in DEFAULT_HEADERS
    ]


def get_monthly_sheet_name(when=None):
    """
    Returns the sheet name in 'YYYY-MM' format.
    Enforces chronological sorting and clean archiving.
    """
    stamp = _parse_date(when) or datetime.now()
    return stamp.strftime("%Y-%m")


def get_sheets_service():
    credentials, _ = google.auth.default(scopes=SCOPES)
    return build("sheets", "v4", credentials=credentials)


def _month_anchor(month=None, year=None, date_value=None):
    if date_value:
        return date_value
    if month or year:
        try:
            y = int(year) if year else datetime.now().year
            m = int(month) if month else datetime.now().month
            return datetime(y, m, 1).strftime("%Y-%m-%d")
        except Exception:
            return None
    return datetime.now().strftime("%Y-%m-%d")


class SheetsLedgerStore:
    def __init__(self, service=None, spreadsheet_id=None):
        self._service = service
        self._spreadsheet_id = spreadsheet_id
        self._logger = logging.getLogger("finance_proxy.ledger")

    def _ensure_service(self):
        if self._service is not None:
            return self._service
        try:
            self._service = get_sheets_service()
        except Exception as exc:
            raise RuntimeError(
                "google.auth and googleapiclient are required to initialize Sheets access"
            ) from exc
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
            
        # 1. Create Sheet
        batch_update = {"requests": [{"addSheet": {"properties": {"title": month_name}}}]}
        res = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=batch_update,
        ).execute()
        
        sheet_id = res["replies"][0]["addSheet"]["properties"]["sheetId"]

        # 2. Add Headers
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{month_name}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [DEFAULT_HEADERS]},
        ).execute()

        # 3. Add Data Validation (Dropdowns) for Pillars (E), Integrity (F), Triggers (G)
        # E is index 4, F is index 5, G is index 6
        validation_requests = {
            "requests": [
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1, # Skip header
                            "startColumnIndex": 4, # E
                            "endColumnIndex": 5, 
                        },
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [{"userEnteredValue": v} for v in MACHINE_PILLARS],
                            },
                            "showCustomUi": True,
                            "strict": True,
                        },
                    }
                },
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": 5, # F
                            "endColumnIndex": 6,
                        },
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [{"userEnteredValue": v} for v in INTEGRITY_FILTERS],
                            },
                            "showCustomUi": True,
                            "strict": True,
                        },
                    }
                },
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": 6, # G
                            "endColumnIndex": 7,
                        },
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [{"userEnteredValue": v} for v in ROOT_TRIGGERS],
                            },
                            "showCustomUi": True,
                            "strict": True,
                        },
                    }
                },
            ]
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=validation_requests
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

    def list_transactions(self, month=None, year=None, date=None, date_value=None):
        service = self._ensure_service()
        spreadsheet_id = self._ensure_spreadsheet_id()

        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        locale = spreadsheet.get("properties", {}).get("locale", "en_US")
        sheet_names = [
            sheet.get("properties", {}).get("title", "")
            for sheet in spreadsheet.get("sheets", [])
        ]

        if date_value is None:
            date_value = date
        anchor = _month_anchor(month=month, year=year, date_value=date_value)
        anchor = _month_anchor(month=month, year=year, date_value=date_value)
        month_name = get_monthly_sheet_name(when=anchor)

        if month_name not in sheet_names:
            return {"month": month_name, "count": 0, "transactions": []}

        values = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=f"'{month_name}'!A:D",
            )
            .execute()
            .get("values", [])
        )

        start_index = 1 if values and _row_is_header(values[0]) else 0
        transactions = []
        for i, row in enumerate(values[start_index:]):
            # A:Date, B:Desc, C:Amount, D:Cat, E:Pillar, F:Integrity, G:Trigger, H:Notes
            # Handle potential missing columns gracefully
            row_date = _normalize_date(row[0]) if len(row) > 0 else ""
            row_desc = str(row[1]).strip() if len(row) > 1 else ""
            row_amount = str(row[2]).strip() if len(row) > 2 else ""
            row_cat = str(row[3]).strip() if len(row) > 3 else ""
            
            # New columns
            row_pillar = str(row[4]).strip() if len(row) > 4 else ""
            row_integrity = str(row[5]).strip() if len(row) > 5 else ""
            row_trigger = str(row[6]).strip() if len(row) > 6 else ""
            row_notes = str(row[7]).strip() if len(row) > 7 else ""

            if not any([row_date, row_desc, row_cat, row_amount]):
                continue
            
            # Grounding: Calculate physical row ID (1-based index)
            # start_index is usually 1 (header), plus current loop index i, plus 1 for 1-based.
            physical_row_id = start_index + i + 1

            transactions.append(
                {
                    "row_id": physical_row_id,
                    "date": row_date,
                    "description": row_desc,
                    "amount": row_amount,
                    "category": row_cat,
                    "machine_pillar": row_pillar,
                    "integrity_filter": row_integrity,
                    "root_trigger": row_trigger,
                    "notes": row_notes,
                }
            )

        return {"month": month_name, "count": len(transactions), "transactions": transactions}

    def append_transaction(self, amount, description, category="Misc", date_value=None, 
                         machine_pillar="", integrity_filter="", root_trigger="", notes=""):
        service = self._ensure_service()
        spreadsheet_id = self._ensure_spreadsheet_id()

        description = (description or "").strip() or "Unknown"
        category = (category or "").strip() or "Uncategorized"
        date_value = _normalize_date(date_value) or datetime.now().strftime("%Y-%m-%d")

        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        locale = spreadsheet.get("properties", {}).get("locale", "en_US")
        sheet_names = [
            sheet.get("properties", {}).get("title", "")
            for sheet in spreadsheet.get("sheets", [])
        ]

        month_name = get_monthly_sheet_name(when=date_value)

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

        # Schema: Date, Description, Amount, Category, Pillar, Integrity, Trigger, Notes
        row = [
            date_value, 
            description, 
            amount, 
            category,
            machine_pillar,
            integrity_filter,
            root_trigger,
            notes
        ]
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{month_name}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        ).execute()

        self._logger.info("Ledger appended: %s %s %s", date_value, amount, description)
        return {"status": "appended", "message": f"Success: Logged to '{month_name}' tab."}

    def append_transactions(self, transactions):
        appended = 0
        duplicates = 0
        results = []
        for item in transactions:
            res = self.append_transaction(
                amount=item.get("amount"),
                description=item.get("description"),
                category=item.get("category"),
                date_value=item.get("date"),
                machine_pillar=item.get("machine_pillar"),
                integrity_filter=item.get("integrity_filter"),
                root_trigger=item.get("root_trigger"),
                notes=item.get("notes"),
            )
            results.append(res)
            if res.get("status") == "appended":
                appended += 1
            elif res.get("status") == "duplicate":
                duplicates += 1
        return {"appended": appended, "duplicates": duplicates, "results": results}
