import asyncio
from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_gwp(assessment_report):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT gas, gwp as gwp100, assessment_report FROM gwp WHERE assessment_report = %s;",
                (assessment_report,),
            )
            rows = await cur.fetchall()
            return rows


@router.get("/gwp")
async def gwp(assessment_report: str = "AR6"):
    """
    Returns global warming potentials (GWP)
    from a specific assessment report.
    """
    data = await fetch_gwp(assessment_report)
    return data
