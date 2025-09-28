import asyncio
from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_actor_contextual(actor_id):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT 
                    COALESCE(p.year, g.year) AS year,
                    p.population,
                    p.datasource_id AS population_datasource,
                    g.gdp,
                    g.datasource_id AS gdp_datasource
                FROM population p
                FULL OUTER JOIN gdp g
                    ON p.actor_id = g.actor_id AND p.year = g.year
                WHERE (p.actor_id = %s OR g.actor_id = %s)
                ORDER BY year;
                """,
                (actor_id, actor_id),
            )
            rows = await cur.fetchall()
            return rows


@router.get("/contextual/{actor_id}", tags=["contextual"])
async def actor_population(actor_id: str):
    """Returns population for particular actor"""
    data = await fetch_actor_contextual(actor_id)
    return data
