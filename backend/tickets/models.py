from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SupportTicket(BaseModel):
    ticket_id:str
    customer:Optional[str]=None
    order_id:Optional[str]=None
    product:Optional[str]=None

    issue:str

    evidence:Optional[str]=None
    contact_details:Optional[str]=None

    sentiment: str = "Neutral"
    sentiment_confidence: float = 0.0

    severity: str = "Medium"
    priority: str = "Medium"

    status: str = "Open"

    created_at: datetime = Field(
        default_factory=datetime.now
    )   