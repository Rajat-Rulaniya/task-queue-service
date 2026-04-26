from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings
from models import Job


async def init_db():
    """Initialize MongoDB connection and Beanie"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB],
        document_models=[Job]
    )
    return client


async def close_db(client: AsyncIOMotorClient):
    """Close MongoDB connection"""
    client.close()
