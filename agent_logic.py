import os
from datetime import datetime
from dotenv import load_dotenv

# Lazy/optional imports to make the module import-safe in test environments
try:
    from langchain_core.tools import tool as _lc_tool
    # wrap the langchain tool so it registers the tool but leaves the
    # original function callable for testing.
    def tool(fn=None, **kwargs):
        if fn is None:
            def _dec(f):
                try:
                    _lc_tool(**kwargs)(f)
                except Exception:
                    pass
                return f
            return _dec
        else:
            try:
                _lc_tool(**kwargs)(fn)
            except Exception:
                pass
            return fn
except Exception:
    # fallback no-op decorator when langchain isn't installed (for tests)
    def tool(fn=None, **_kwargs):
        if fn is not None:
            return fn
        def _dec(f):
            return f
        return _dec

load_dotenv()

# 1. Configuration & Constants
load_dotenv()
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_localized_month_name(service, spreadsheet_id):
    """
    Looks at the spreadsheet's locale (IT, SV, EN) and returns 
    the current month name in that specific language.
    """
    res = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    locale = res.get('properties', {}).get('locale', 'en_US')
    # locale looks like en_US, sv_SE, it_IT etc. Extract language code.
    lang_code = (locale.split('_')[0].lower() if locale else "en")

    month_maps = {
     "sv": ["Januari", "Februari", "Mars", "April", "Maj", "Juni", 
         "Juli", "Augusti", "September", "Oktober", "November", "December"],
     "it": ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
         "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"],
     "en": ["January", "February", "March", "April", "May", "June", 
         "July", "August", "September", "October", "November", "December"]
    }

    # Default to English if the locale isn't in our map
    month_list = month_maps.get(lang_code, month_maps["en"])
    return month_list[datetime.now().month - 1]

# 2. The Tools
@tool
def append_to_spreadsheet(amount: float, description: str, category: str = "Misc", *, service=None, spreadsheet_id=None):
    """
    Logs a transaction to the finance ledger. 
    Args:
        amount: The numerical value (use negative for expenses).
        description: A short note about the transaction.
        category: The budget category (e.g., Food, Travel).
    """
    # Allow injection of a fake service (for testing). If not provided, do a real auth.
    if service is None:
        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
        except Exception as e:
            raise RuntimeError("googleapiclient and google.oauth2 are required when no service is passed") from e

        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not spreadsheet_id:
            spreadsheet_id = os.getenv("LEDGER_SPREADSHEET_ID")

        creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
    else:
        # If a service is provided but no spreadsheet_id argument given, read from env
        if not spreadsheet_id:
            spreadsheet_id = os.getenv("LEDGER_SPREADSHEET_ID")

    # Step A: Get the Month Name dynamically based on Sheet Language
    month_name = get_localized_month_name(service, spreadsheet_id)

    # Step B: Check if that month's tab exists
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_names = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]

    # Step C: Create the tab if it's missing (with headers)
    if month_name not in sheet_names:
        batch_update = {'requests': [{'addSheet': {'properties': {'title': month_name}}}]}
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batch_update).execute()
        
        headers = [["Datum", "Beskrivning", "Kategori", "Belopp"]]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{month_name}'!A1",
            valueInputOption="USER_ENTERED",
            body={'values': headers}
        ).execute()

    # Step D: Append the actual transaction
    row = [datetime.now().strftime("%Y-%m-%d"), description, category, amount]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{month_name}'!A1",
        valueInputOption="USER_ENTERED",
        body={'values': [row]}
    ).execute()

    return f"Success: Logged to '{month_name}' tab."

# 3. The Agent Class
class FinanceAnalystAgent:
    def __init__(self):
        self.executor = None

    def set_up(self):
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate
        
        # Explicit Vertex AI Config
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            temperature=0,
            vertexai=True,
            project=os.getenv("GCP_PROJECT_ID"),
            location=os.getenv("GCP_LOCATION", "europe-west1")
        )
        
        # System instructions that handle all your languages
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a multilingual Personal Finance Assistant. 
             You can understand Swedish, Italian, and English.
             Always log expenses as negative numbers.
             If a category isn't clear, use your best judgment or ask for clarification."""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        agent_tools = [append_to_spreadsheet]
        agent = create_tool_calling_agent(llm, agent_tools, prompt)
        self.executor = AgentExecutor(agent=agent, tools=agent_tools, verbose=True)

    def query(self, input_text: str):
        if not self.executor:
            self.set_up()
        return self.executor.invoke({"input": input_text})["output"]