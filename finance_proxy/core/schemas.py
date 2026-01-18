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
