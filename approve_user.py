import motor.motor_asyncio
import asyncio
from beanie import init_beanie, Document, Indexed
from datetime import datetime
from typing import Optional
from pydantic import Field

class UserLicense(Document):
    userId: Indexed(str, unique=True)
    username: Indexed(str, unique=True)
    email: Optional[str] = None
    hashed_password: str
    status: bool = False
    reset_otp: Optional[str] = None
    predictionCount: int = 0
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "user_licenses"

async def approve_user(username):
    connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    await init_beanie(database=client['kp_astrologer_db'], document_models=[UserLicense])
    
    user = await UserLicense.find_one(UserLicense.username == username)
    if user:
        user.status = True
        await user.save()
        print(f"User {username} approved successfully.")
    else:
        print(f"User {username} not found.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python approve_user.py <username>")
    else:
        asyncio.run(approve_user(sys.argv[1]))
