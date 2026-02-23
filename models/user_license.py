from datetime import datetime
from typing import Optional, Annotated
from beanie import Document, Indexed
from pydantic import Field, ConfigDict

class UserLicense(Document):
    userId: Annotated[str, Indexed(unique=True)]
    username: Annotated[str, Indexed(unique=True)]
    email: Optional[str] = None
    hashed_password: str
    status: bool = False  # Approved by owner
    reset_otp: Optional[str] = None
    predictionCount: int = 0
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "user_licenses"
