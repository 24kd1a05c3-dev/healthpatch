from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
from typing_extensions import Literal

TriggerSource = Literal["patient", "system", "caregiver"]
EmergencyStatus = Literal["active", "responding", "resolved"]

class EmergencyCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    triggered_by: TriggerSource = "patient"
    location: Optional[Dict[str, Any]] = None
    notes: Optional[str] = Field(default=None, max_length=2000)

class EmergencyEvent(BaseModel):
    user_id: str
    triggered_by: TriggerSource
    health_snapshot: Dict[str, Any]
    location: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    status: EmergencyStatus = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

class EmergencyResponse(EmergencyEvent):
    id: str
    model_config = ConfigDict(from_attributes=True)
