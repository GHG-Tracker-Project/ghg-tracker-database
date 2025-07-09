import asyncio
from fastapi import APIRouter
import psycopg

# database_url = "postgresql://postgres:postgres@127.0.0.1:5432/ghgtracker"
database_url = "postgresql://postgres:postgres@postgres_db:5432/ghgtracker"

router = APIRouter()


async def fetch_actors():
    async with await psycopg.AsyncConnection.connect(database_url) as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute("SELECT id, name, type, is_part_of FROM actor;")
            rows = await cur.fetchall()
            return rows


async def fetch_actors_parts(is_part_of):
    async with await psycopg.AsyncConnection.connect(database_url) as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT id, name, type, is_part_of FROM actor WHERE is_part_of = %s;",
                (is_part_of,),
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
    ## Actors
    Endpoint to get information on each actor in the database
    Returns:
        ActorModel: information on each actor
    """
    data = await fetch_actors()
    return data


@router.get("/part_of/{actor_id}")
async def read_parts(actor_id: str):
    data = await fetch_actors_parts(actor_id)
    return data
