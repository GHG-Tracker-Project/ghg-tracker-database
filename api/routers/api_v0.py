from fastapi import APIRouter
from routers import (
    actor,
    emissions,
    gdp,
    gwp,
    health,
    population,
    root,
    targets,
)

api_router = APIRouter(prefix="/api/v0")

api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(actor.router)
api_router.include_router(population.router)
api_router.include_router(gdp.router)
api_router.include_router(gwp.router)
api_router.include_router(targets.router)
api_router.include_router(emissions.router)
