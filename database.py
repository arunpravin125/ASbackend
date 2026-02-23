import motor.motor_asyncio
from beanie import init_beanie
from models.user_license import UserLicense
from models.prediction import Prediction
import os

async def init_db():
    # MongoDB connection string provided by user
    connection_string = "mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0"
    
    # Create Motor client
    client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
    
    # Initialize beanie with the UserLicense and Prediction document models
    await init_beanie(database=client['kp_astrologer_db'], document_models=[UserLicense, Prediction])
    print("Database initialized successfully")
