import motor.motor_asyncio
import asyncio

async def drop_indexes():
    print("Connecting to DB...")
    connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    db = client['kp_astrologer_db']
    col = db['user_licenses']
    
    print("Dropping all indexes...")
    try:
        await col.drop_indexes()
        print("All indexes dropped successfully.")
    except Exception as e:
        print(f"Failed to drop indexes: {e}")

if __name__ == "__main__":
    asyncio.run(drop_indexes())
