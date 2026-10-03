from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from typing_extensions import Literal

AlertLevel = Literal["info", "warning", "critical"]

class Alert(BaseModel):
    user_id: str
    alert_type: str
    level: AlertLevel = "info"
    title: str
    message: str
    reasons: List[str] = Field(default_factory=list)
    anomaly_score: Optional[float] = None
    device_id: str
    measurement_id: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AlertResponse(Alert):
    id: str
    model_config = ConfigDict(from_attributes=True)

class AlertAcknowledge(BaseModel):
    acknowledged_by: Optional[str] = None
