import asyncio
from fastapi import APIRouter
import psycopg

# database_url = "postgresql://postgres:postgres@127.0.0.1:5432/ghgtracker"
database_url = "postgresql://postgres:postgres@postgres_db:5432/ghgtracker"

router = APIRouter()


async def fetch_actor_targets(actor_id):
    async with await psycopg.AsyncConnection.connect(database_url) as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT actor_id, target_type, baseline_year, target_year, target_value AS percent_reduction, url FROM targets WHERE actor_id = %s;",
                (actor_id,),
            )
            rows = await cur.fetchall()
            return rows


@router.get("/targets/{actor_id}")
async def actor_targets(actor_id: str):
    data = await fetch_actor_targets(actor_id)
    return data
