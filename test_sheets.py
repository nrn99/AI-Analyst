# test_sheets.py
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

# 1. Load your credentials
load_dotenv()
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
spreadsheet_id = os.getenv("LEDGER_SPREADSHEET_ID")

print(f"--- Connection Test ---")
print(f"Key Path: {key_path}")
print(f"Sheet ID: {spreadsheet_id}")
 
try:
    # 2. Authenticate
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)


    # 3. Get the dynamic name of the FIRST tab
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    # This gets the title of the very first sheet in the workbook
    first_sheet_name = spreadsheet.get('sheets', [])[0]['properties']['title']

    print(f"Detected primary tab name: '{first_sheet_name}'")

    # 4. Use that name for the append
    test_row = [["2026-01-06", "Cross-Language Test", "System", "0"]]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{first_sheet_name}'!A1", # Added single quotes in case of spaces
        valueInputOption="USER_ENTERED",
        body={'values': test_row}
    ).execute()
    print(f"✅ SUCCESS: Appended to '{first_sheet_name}'!")

except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")
    