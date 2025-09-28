import asyncio
from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_actors():
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute("SELECT id, name, type, is_part_of FROM actor;")
            rows = await cur.fetchall()
            return rows


async def fetch_actors_parts(is_part_of, actor_type):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            if actor_type is None:
                await cur.execute(
                    "SELECT id, name, type, is_part_of FROM actor WHERE is_part_of = %s;",
                    (is_part_of,),
                )
            else:
                await cur.execute(
                    "SELECT id, name, type, is_part_of FROM actor WHERE is_part_of = %s AND type = %s;",
                    (is_part_of, actor_type),
                )
            rows = await cur.fetchall()
            return rows


@router.get(
    "/actors",
    tags=["actors"],
    summary="get all actors",
    response_description="returns information on each actor",
)
async def read_actors():
    """
    Returns information on each actor in the database
    """
    data = await fetch_actors()
    return data


@router.get(
    "/parts_of/{actor_id}",
    tags=["actors"],
)
async def read_parts(actor_id: str, type: str = None):
    """
    Returns the parts of each actor.

    Can filter by `type`, which can be `adm1`, `adm2`, or `city`
    """
    data = await fetch_actors_parts(actor_id, type)
    return data
