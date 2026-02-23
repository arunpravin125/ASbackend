from datetime import datetime
from typing import Optional, Dict, Any
from beanie import Document, Indexed
from pydantic import Field

class Prediction(Document):
    userId: Indexed(str)
    team_a: str
    team_b: str
    datetime_utc: datetime
    lat: float
    lon: float
    muhurta_analysis: Optional[Dict[str, Any]] = None
    createdAt: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "predictions"
