from fastapi import APIRouter
from routers import actor, health, root

api_router = APIRouter(prefix="/api/v0")

api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(actor.router)
