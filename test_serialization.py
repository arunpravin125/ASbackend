import asyncio
import uuid
from typing import Optional, Annotated
from beanie import Document, Indexed, init_beanie
from pydantic import Field, ConfigDict
from datetime import datetime
import motor.motor_asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from models.user_license import UserLicense

async def test_serialization():
    print("--- Testing UserLicense Serialization ---")
    
    # connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    # client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    # await init_beanie(database=client['kp_astrologer_db'], document_models=[UserLicense])

    user = UserLicense(
        userId=str(uuid.uuid4()),
        username="test_user",
        email="test@example.com",
        hashed_password="hash",
        status=False
    )
    
    print(f"User object: {user}")
    print(f"Model dump: {user.model_dump()}")
    
    # Check if userId is for some reason not in the dump
    if 'userId' not in user.model_dump():
        print("CRITICAL: userId is REMOVED from model_dump!")
    elif user.model_dump()['userId'] is None:
        print("CRITICAL: userId is NONE in model_dump!")
    else:
        print(f"userId in dump: {user.model_dump()['userId']}")

if __name__ == "__main__":
    asyncio.run(test_serialization())
