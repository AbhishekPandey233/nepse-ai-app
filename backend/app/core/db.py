from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_default_database()


def get_database():
    return db
