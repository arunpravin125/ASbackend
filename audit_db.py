import motor.motor_asyncio
import asyncio

async def audit():
    connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    db = client['kp_astrologer_db']
    col = db['user_licenses']
    
    print("--- Detailed Audit ---")
    cursor = col.find({})
    async for doc in cursor:
        print(f"Record: {doc}")

if __name__ == "__main__":
    asyncio.run(audit())
