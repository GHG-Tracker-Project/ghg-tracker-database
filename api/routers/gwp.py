import asyncio
from fastapi import APIRouter
import psycopg

# database_url = "postgresql://postgres:postgres@127.0.0.1:5432/ghgtracker"
database_url = "postgresql://postgres:postgres@postgres_db:5432/ghgtracker"

router = APIRouter()


async def fetch_gwp(assessment_report):
    async with await psycopg.AsyncConnection.connect(database_url) as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT gas, gwp as gwp100, assessment_report FROM gwp WHERE assessment_report = %s;",
                (assessment_report,),
            )
            rows = await cur.fetchall()
            return rows


@router.get("/gwp")
async def gwp(assessment_report: str = "AR6"):
    data = await fetch_gwp(assessment_report)
    return data
