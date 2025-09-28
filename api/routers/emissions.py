import asyncio
from fastapi import APIRouter, Query
import psycopg
from collections import defaultdict

from db.session import get_connection

router = APIRouter()


async def fetch_actor_emissions(actor_id, assessment_report=None):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            if assessment_report and assessment_report.lower() == "all":
                # Return all data across all assessment reports
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %s AND aggregation_type = 'total_ex_lulucf'
                    """,
                    (actor_id,),
                )
                rows = await cur.fetchall()
                return rows

            elif assessment_report:
                # Filter for a specific assessment report
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %s AND aggregation_type = 'total_ex_lulucf'
                    AND assessment_report = %s;
                    """,
                    (actor_id, assessment_report),
                )
                rows = await cur.fetchall()
                return rows

            else:
                # No assessment_report specified: find the most recent with data
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %s AND aggregation_type = 'total_ex_lulucf'
                    AND assessment_report IN ('AR6','AR5','AR4','AR3','AR2')
                    ORDER BY 
                        CASE assessment_report
                            WHEN 'AR6' THEN 1
                            WHEN 'AR5' THEN 2
                            WHEN 'AR4' THEN 3
                            WHEN 'AR3' THEN 4
                            WHEN 'AR2' THEN 5
                            ELSE 6
                        END
                    """,
                    (actor_id,),
                )
                rows = await cur.fetchall()

                # Group by assessment_report, pick the first with data
                grouped = defaultdict(list)
                for row in rows:
                    grouped[row["assessment_report"]].append(row)

                for ar in ["AR6", "AR5", "AR4", "AR3", "AR2"]:
                    if ar in grouped:
                        return grouped[ar]

                return []


@router.get("/emissions/{actor_id}", tags=["emissions"])
async def actor_emissions(
    actor_id: str,
    assessment_report: str = Query(
        None,
        description="Filter by assessment report (e.g. AR6), or use 'all' to get all data",
    ),
):
    """
    Returns total emissions excluding LULUCF for a particular actor.
    - If assessment_report is provided, filters by that report (or returns all if 'all').
    - If not provided, returns data from the most recent report with data.
    Units are tonnes of CO2-eq.
    """
    data = await fetch_actor_emissions(actor_id, assessment_report)
    return data
