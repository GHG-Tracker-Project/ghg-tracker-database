# FastAPI for GHG Tracker Database

REST API layer built using [FastAPI](https://fastapi.tiangolo.com/) and connects to the database using [psycopg](https://www.psycopg.org/psycopg3/)

## Starting the API server

From this directory, you can start the uvicorn server with:

```python
uv run python -m uvicorn main:app --reload
```

## Directory structure

```
.
├── README.md # top level readme
├── main.py   # main entrypoint to the api
└── routers   # all the api routes
    ├── __init__.py # to make this a python package
    ├── actor.py    # information on the actors
    ├── api_v0.py   # connects all the routes together
    ├── health.py   # health status check
    └── root.py     # root endpoint
```

> [!NOTE]  
> This is a work in progress. Still working on the best schema that will be useful for a high-level Python client
