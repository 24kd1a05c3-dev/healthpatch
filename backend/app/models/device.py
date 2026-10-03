from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from typing_extensions import Literal

DeviceStatus = Literal["ONLINE", "OFFLINE", "LOW_BATTERY", "SYNCING", "ERROR"]

class DeviceCreate(BaseModel):
    device_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")
    firmware_version: str = Field(default="1.0.0", max_length=40)

class DeviceResponse(BaseModel):
    device_id: str
    user_id: Optional[str] = None
    status: DeviceStatus
    battery: Optional[int] = None
    signal_quality: Optional[float] = None
    last_seen: Optional[datetime] = None
    firmware_version: str
    model_name: str = "HealthPatch"
    model_config = ConfigDict(from_attributes=True)

class DevicePair(BaseModel):
    user_id: str
