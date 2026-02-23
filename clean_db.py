import motor.motor_asyncio
import asyncio

async def clean():
    print("Connecting to DB...")
    connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    db = client['kp_astrologer_db']
    col = db['user_licenses']
    
    print("Deleting all records from user_licenses...")
    res = await col.delete_many({})
    print(f"Deleted {res.deleted_count} records.")

if __name__ == "__main__":
    asyncio.run(clean())
