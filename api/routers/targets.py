import asyncio
from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_actor_targets(actor_id):
    async with await get_connection() as conn:
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
