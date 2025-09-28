import asyncio
from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_actor_population(actor_id):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT actor_id, year, population, datasource_id FROM population WHERE actor_id = %s;",
                (actor_id,),
            )
            rows = await cur.fetchall()
            return rows


@router.get("/population/{actor_id}", tags=["contextual"])
async def actor_population(actor_id: str):
    """Returns population for particular actor"""
    data = await fetch_actor_population(actor_id)
    return data
