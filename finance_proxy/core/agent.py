import logging
import json
from datetime import datetime
import vertexai
from vertexai.preview.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
    Content,
    Part,
)
from .ledger import SheetsLedgerStore
from .categories import FIXED_CATEGORIES
from pydantic import BaseModel, Field
from typing import Optional

class Transaction(BaseModel):
    row_id: int = Field(..., description="The physical row number in the spreadsheet (Grounding).")
    date: str = Field(..., description="Transaction date YYYY-MM-DD.")
    description: str = Field(..., description="Details of the transaction.")
    amount: float = Field(..., description="Amount in SEK.")
    category: str = Field(..., description="Expense category.")
    machine_pillar: Optional[str] = Field(None, description="The Financial Machine Pillar.")
    integrity_filter: Optional[str] = Field(None, description="Integrity check status.")
    root_trigger: Optional[str] = Field(None, description="Root emotional trigger.")
    notes: Optional[str] = Field(None, description="User notes.")

class FinanceAnalystAgent:
    def __init__(self, model_name: str = "gemini-2.0-flash-001", project: str = None, location: str = "europe-west1"):
        self.model_name = model_name
        self.project = project
        self.location = location
        self.ledger = SheetsLedgerStore()
        self._model = None
        self._chat = None

    def set_up(self):
        """Initializes the Vertex AI model and tools."""
        if self._model:
            return

        if self.project:
            vertexai.init(project=self.project, location=self.location)

        # Define FunctionDeclarations manually for robustness
        list_transactions_func = FunctionDeclaration(
            name="list_transactions",
            description="Get the last n transactions from the ledger.",
            parameters={
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of transactions to return. Default is 5."
                    }
                },
            },
        )

        get_uncategorized_func = FunctionDeclaration(
            name="get_uncategorized",
            description="Get all transactions that are uncategorized.",
            parameters={
                "type": "object",
                "properties": {},
            },
        )

        # Create Tool with declarations
        self.finance_tool = Tool(
            function_declarations=[list_transactions_func, get_uncategorized_func]
        )
        
        # Core System Prompt - The Financial Machine
        system_prompt = f"""You are The Financial Machine (TFM).
Your Core Directive: Protect the user's cash flow, align spending with faith, and ensure reliable growth.
You are COLD on data but WARM on mission.
You value RADICAL TRUTH over comfort.

# The 4 Pillars of Execution:
1. Stewardship (Faith): Tithe/Charity must happen first.
2. Reality (Needs): Survival costs (Housing/Food) <= 40% of income.
3. Integrity (Wants): Monitor Impulse buys.
4. Strategy (Growth): Protect the base (Savings).

# GROUNDING RULE (CRITICAL):
You must NEVER hallucinate or guess.
Every fact you state about a transaction MUST be grounded in the ledger.
You MUST cite the physical 'Row ID' for every specific transaction you reference.
Example: "You spent 500 SEK on Groceries (Row 14)."

The available categories are: {', '.join(FIXED_CATEGORIES)}.
"""
        
        self._model = GenerativeModel(
            self.model_name,
            tools=[self.finance_tool],
            system_instruction=system_prompt
        )
        self._chat = self._model.start_chat()

    def list_transactions(self, n: int = 5) -> str:
        """Get the last n transactions from the ledger."""
        data = self.ledger.list_transactions()
        txs = data.get("transactions", [])
        # Pydantic validation (ensure data integrity)
        validated = [Transaction(**t).model_dump() for t in txs[-n:]]
        return json.dumps(validated, default=str)

    def get_uncategorized(self) -> str:
        """Get all transactions that are uncategorized."""
        data = self.ledger.list_transactions()
        txs = [t for t in data.get("transactions", []) if t.get("category") == "Uncategorized"]
        return json.dumps(txs, default=str)

    def query(self, prompt: str = None, input: str = None, **kwargs) -> str:
        prompt = prompt or input or kwargs.get("question") or "So, what's up?"
        """Query the agent with a natural language question."""
        if not self._model:
            self.set_up()

        # Simple ReAct loop (handled by start_chat + automatic function calling is not implicit in Python SDK yet for all versions)
        # We will use the automatic function calling feature of chat.send_message if available
        # OR manually loop. Safer to manual loop for now to be robust.
        
        response = self._chat.send_message(prompt)
        
        # Detailed loop handling
        params = {}
        function_call = response.candidates[0].content.parts[0].function_call
        
        while function_call.name:
            function_name = function_call.name
            args = {k: v for k, v in function_call.args.items()}
            
            result = None
            if function_name == "list_transactions":
                result = self.list_transactions(**args)
            elif function_name == "get_uncategorized":
                result = self.get_uncategorized()
            else:
                result = "Error: Unknown function"
                
            # Send result back
            response = self._chat.send_message(
                Part.from_function_response(
                    name=function_name,
                    response={"content": result}
                )
            )
            # Check next response
            if not response.candidates[0].content.parts:
                break
            if response.candidates[0].content.parts[0].function_call:
                function_call = response.candidates[0].content.parts[0].function_call
            else:
                break

        return response.text
