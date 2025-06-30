# FastAPI for GHG Tracker Database

REST API layer built using [FastAPI](https://fastapi.tiangolo.com/) and connects to the database using [psycopg](https://www.psycopg.org/psycopg3/). Note that we currently have the database URL hardcoded in each file. Need to fix this

## Starting the API server

From this directory, you can start the dev api server with:

```bash
fastapi dev main.py
```

or from main directory

```bash
fastapi dev ./api/main.py
```

## Directory structure

```
.
├── README.md         # top-level readme
├── main.py           # main entrypoint for the api
└── routers           # all the api routes
    ├── __init__.py   # to make this a python package
    ├── actor.py      # information on the actors
    ├── api_v0.py     # connects all the routes together
    ├── gdp.py        # gdp time series for an actor
    ├── gwp.py        # gwp from specific assessment report
    ├── health.py     # health status check
    ├── population.py # population time series for an actor
    ├── root.py       # root endpoint
    └── targets.py    # emission target for an actor
```

> [!NOTE]  
> This is a work in progress. Still working on the best schema that will be useful for a high-level Python client
