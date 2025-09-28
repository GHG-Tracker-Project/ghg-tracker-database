import asyncio
from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_actor_gdp(actor_id):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT actor_id, year, gdp, datasource_id FROM gdp WHERE actor_id = %s;",
                (actor_id,),
            )
            rows = await cur.fetchall()
            return rows


@router.get("/gdp/{actor_id}", tags=["contextual"])
async def actor_gdp(actor_id: str):
    """Returns gross domestic product (GDP) for particular actor"""
    data = await fetch_actor_gdp(actor_id)
    return data
