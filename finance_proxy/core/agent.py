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
        
        self._model = GenerativeModel(
            self.model_name,
            tools=[self.finance_tool],
            system_instruction=f"You are a helpful financial analyst. You have access to a ledger of transactions. The available categories are: {', '.join(FIXED_CATEGORIES)}."
        )
        self._chat = self._model.start_chat()

    def list_transactions(self, n: int = 5) -> str:
        """Get the last n transactions from the ledger.
        
        Args:
            n: Number of transactions to return.
        """
        data = self.ledger.list_transactions()
        txs = data.get("transactions", [])
        return json.dumps(txs[-n:], default=str)

    def get_uncategorized(self) -> str:
        """Get all transactions that are uncategorized."""
        data = self.ledger.list_transactions()
        txs = [t for t in data.get("transactions", []) if t.get("category") == "Uncategorized"]
        return json.dumps(txs, default=str)

    def query(self, input: str) -> str:
        """Query the agent with a natural language question."""
        if not self._model:
            self.set_up()

        # Simple ReAct loop (handled by start_chat + automatic function calling is not implicit in Python SDK yet for all versions)
        # We will use the automatic function calling feature of chat.send_message if available
        # OR manually loop. Safer to manual loop for now to be robust.
        
        response = self._chat.send_message(input)
        
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
