"""
This script pulls state population data using the Fred API, this requires an API key
You can obtain an API key here: https://fred.stlouisfed.org/docs/api/api_key.html
"""

import asyncio
from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv
import httpx
import pandas as pd

from models import DataSource, Population
from utils import write_csv


async def main():
    envfile = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=envfile)
    # print(os.getenv("FRED_API_KEY"))

    # load data
    folder_name = Path(__file__).resolve().parent.stem
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / f"{folder_name}"
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------
    # get states from actor table
    # ------------------------------------------
    actors_file = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "iso-3166-2"
        / "processed"
        / "actor.csv"
    )
    df_actors = pd.read_csv(actors_file)
    df_states = df_actors.query("is_part_of == 'US'").assign(
        state_code=lambda x: x.apply(lambda row: row["id"].split("-")[1], axis=1)
    )[["id", "state_code", "name"]]

    # ------------------------------------------
    # datasource dictonary
    # ------------------------------------------
    datasources = []

    for row in df_states.itertuples():
        datasource_name = f"{row.state_code}POP"
        publisher = "fred"

        datasource = DataSource(
            id=f"{publisher}:{datasource_name}",
            name=f"Resident Population {row.name}",
            publisher=publisher,
            published_date=datetime.strptime("2024-08-29", "%Y-%m-%d"),
            url=f"https://fred.stlouisfed.org/series/{row.state_code}POP",
        )

        dic = {row.id: datasource}
        datasources.append(dic)

    datasource_dic = {k: v for d in datasources for k, v in d.items()}

    # ------------------------------------------
    # Population table
    # ------------------------------------------
    async def population_by_state(client: httpx.AsyncClient, state, api_key):
        base_api = "https://api.stlouisfed.org/fred/series/observations"
        query = f"{base_api}?series_id={state}POP&api_key={api_key}&file_type=json"
        response = await client.get(query)
        return state, response.json()

    df_actors = pd.read_csv(
        "/Users/lukegloege/projects/ghg-tracker-database/data/iso-3166-2/processed/actor.csv"
    )
    states = [
        state.split("-")[1]
        for state in df_actors.query("is_part_of == 'US'")["id"].values
    ]
    api_key = os.getenv("FRED_API_KEY")

    async with httpx.AsyncClient() as client:
        tasks = [population_by_state(client, state, api_key) for state in states]
        results = await asyncio.gather(*tasks)

    dfs = []
    for state_code, result in results:
        if "observations" in result:
            df = pd.DataFrame(result["observations"]).assign(state=state_code)
            dfs.append(df)

    df = pd.concat(dfs, ignore_index=True).assign(
        date=lambda x: pd.to_datetime(x["date"]),
        year=lambda x: x["date"].dt.year,
        value=lambda x: pd.to_numeric(x["value"], errors="coerce"),
        population=lambda x: x["value"] * 1000,
        actor_id=lambda x: x.apply(lambda row: f"US-{row['state']}", axis=1),
    )[["actor_id", "year", "population"]]

    population_validated = [
        Population(
            id=f"{row.actor_id}:{row.year}",
            year=row.year,
            actor_id=row.actor_id,
            population=int(row.population),
            datasource_id=datasource_dic.get(row.actor_id).id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Population.__tablename__,
        data=population_validated,
        mode="w",
    )

    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasources_validated = [
        v.model_dump() for k, v in datasource_dic.items() if k in df["actor_id"].values
    ]

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasources_validated,
        mode="w",
    )


if __name__ == "__main__":
    asyncio.run(main())
