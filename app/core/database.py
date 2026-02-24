from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from typing import List, Type
from beanie import Document


# Global motor client
client: AsyncIOMotorClient = None


async def connect_to_mongo():
    """Initialize MongoDB connection and Beanie ODM"""
    global client

    # Determine if SSL should be used based on the URL
    use_ssl = "mongodb+srv://" in settings.MONGODB_URL or "ssl=true" in settings.MONGODB_URL

    # Create MongoDB client with conditional SSL configuration
    client_config = {
        "serverSelectionTimeoutMS": 5000
    }

    if use_ssl:
        # For MongoDB Atlas or SSL-enabled connections
        client_config.update({
            "tls": True,
            "tlsAllowInvalidCertificates": True,  # For MongoDB Atlas
        })

    client = AsyncIOMotorClient(settings.MONGODB_URL, **client_config)

    # Test connection
    try:
        await client.admin.command("ping")
        print(f"✅ Successfully connected to MongoDB: {settings.MONGODB_URL}")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


async def init_beanie_models(document_models: List[Type[Document]]):
    """Initialize Beanie with document models"""
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=document_models
    )
    print(f"✅ Beanie ODM initialized with database: {settings.MONGODB_DB_NAME}")


def get_db():
    """Get database instance"""
    return client[settings.MONGODB_DB_NAME]