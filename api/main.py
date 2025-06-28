from fastapi import FastAPI
from routers.api_v0 import api_router

app = FastAPI()
app.include_router(api_router)
