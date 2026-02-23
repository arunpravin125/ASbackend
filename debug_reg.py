import asyncio
import uuid
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import motor.motor_asyncio
from beanie import init_beanie
from backend.models.user_license import UserLicense
from backend import auth

async def test_reg():
    print("--- DEBUG REG SCRIPT STARTED ---")
    try:
        print("Initializing DB...")
        connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
        client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
        await init_beanie(database=client['kp_astrologer_db'], document_models=[UserLicense])
        print("DB Initialized.")
        
        username = f"test_debug_{int(uuid.uuid4().hex[:8], 16)}"
        password = "testpassword123"
        
        print(f"Hashing password for {username}...")
        try:
            hashed = auth.get_password_hash(password)
            print(f"Hashed: {hashed[:10]}...")
        except Exception as e:
            print(f"Hashing failed: {e}")
            return

        print("Creating user object...")
        new_user = UserLicense(
            userId=str(uuid.uuid4()),
            username=username,
            email="test@example.com",
            hashed_password=hashed,
            status=False
        )
        
        print("Inserting into DB...")
        try:
            await new_user.insert()
            print("Insertion successful!")
        except Exception as e:
            print(f"Insertion failed: {e}")
    except Exception as e:
        print(f"Test failed with top-level error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reg())
