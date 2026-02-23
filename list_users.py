import asyncio
import motor.motor_asyncio
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

async def list_users():
    connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    await init_beanie(database=client['kp_astrologer_db'], document_models=[UserLicense])
    
    users = await UserLicense.find_all().to_list()
    print(f"Total users: {len(users)}")
    for u in users:
        print(f"Username: {u.username}, userId: {u.userId}, ID: {u.id}")

if __name__ == "__main__":
    asyncio.run(list_users())
