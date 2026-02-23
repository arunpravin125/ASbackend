import motor.motor_asyncio
import asyncio
import uuid

async def test_insert():
    print("Connecting to DB...")
    connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    db = client['kp_astrologer_db']
    col = db['user_licenses']
    
    print("Checking indexes...")
    indexes = await col.index_information()
    print(f"Current indexes: {indexes}")
    
    doc = {
        "userId": str(uuid.uuid4()),
        "username": "tester_" + str(uuid.uuid4())[:8],
        "hashed_password": "test",
        "status": False
    }
    
    print(f"Inserting doc: {doc}")
    try:
        res = await col.insert_one(doc)
        print(f"Inserted ID: {res.inserted_id}")
    except Exception as e:
        print(f"Insertion failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_insert())
