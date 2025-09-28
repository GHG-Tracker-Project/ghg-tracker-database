import asyncio

# consider using psycopg_pool
import psycopg

from config import settings

DATABASE_URL = settings.DATABASE_URL
print("Database URL is ", DATABASE_URL)


async def get_connection():
    return await psycopg.AsyncConnection.connect(DATABASE_URL)
