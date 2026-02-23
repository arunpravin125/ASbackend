import asyncio
import motor.motor_asyncio
from beanie import init_beanie, Document
from datetime import datetime
from typing import Optional, Any
from pydantic import Field

class UserLicense(Document):
    userId: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    hashed_password: Optional[str] = None
    status: Optional[bool] = False
    reset_otp: Optional[str] = None
    predictionCount: Optional[int] = 0
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Settings:
        name = "user_licenses"

async def list_users():
    connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    # Initialize beanie without validation if possible, or just with the lenient model
    await init_beanie(database=client['kp_astrologer_db'], document_models=[UserLicense])
    
    # Use motor directly to avoid validation if beanie still fails
    db = client['kp_astrologer_db']
    collection = db['user_licenses']
    
    print("--- Listing all records from user_licenses ---")
    cursor = collection.find({})
    count = 0
    async for doc in cursor:
        count += 1
        print(f"Doc {count}: _id={doc.get('_id')}, username={doc.get('username')}, userId={doc.get('userId')}")
    
    print(f"\nTotal records: {count}")

if __name__ == "__main__":
    asyncio.run(list_users())
