from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class WebhookIn(BaseModel):
    event_id: str
    event_type: str
    payload: dict[str, Any] = {}


class WebhookOut(BaseModel):
    event_id: str
    event_type: str
    payload: dict[str, Any]
    status: str
    attempts: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
