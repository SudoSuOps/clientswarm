"""
MongoDB Database Service
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

from config import get_settings

settings = get_settings()


class Database:
    client: Optional[AsyncIOMotorClient] = None

    @classmethod
    async def connect(cls):
        cls.client = AsyncIOMotorClient(settings.mongodb_url)
        # Create indexes
        db = cls.client[settings.mongodb_db]
        await db.clients.create_index("wallet", unique=True)
        await db.clients.create_index("ens")
        await db.jobs.create_index("client_id")
        await db.jobs.create_index("status")
        await db.jobs.create_index("created_at")

    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()

    @classmethod
    def get_db(cls):
        return cls.client[settings.mongodb_db]


# Collections
def get_clients_collection():
    return Database.get_db().clients


def get_jobs_collection():
    return Database.get_db().jobs


def get_uploads_collection():
    return Database.get_db().uploads
