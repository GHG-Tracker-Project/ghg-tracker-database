from datetime import datetime
from pathlib import Path

import pandas as pd

from models import DataSource, Population
from utils import write_csv


def main():
    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "canada-province-population"
    publisher = "eccc"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="Population estimates, quarterly",
        publisher=publisher,
        published_date=datetime.strptime("2025-06-18", "%Y-%m-%d"),
        url=f"https://open.canada.ca/data/en/dataset/ec690886-687d-4d59-9b1b-51311435d344",
    )

    # load data
    # Note: Path(__file__).resolve().parent.parent same as "../"
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

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
    df_provs = df_actors.query("is_part_of == 'CA'").rename(
        columns={"id": "actor_id", "name": "GEO"}
    )[["actor_id", "GEO"]]

    # ------------------------------------------
    # population table
    # ------------------------------------------
    fl = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "canada-province-population"
        / "raw"
        / "17100009-eng"
        / "17100009.csv"
    )

    df = (
        pd.read_csv(fl)
        .assign(
            year=lambda x: pd.to_datetime(x["REF_DATE"]).dt.year,
            month=lambda x: pd.to_datetime(x["REF_DATE"]).dt.month,
        )
        .rename(columns={"VALUE": "population_quarterly"})
        .merge(df_provs, on="GEO")
        .groupby(["year", "actor_id"])
        .agg(population=("population_quarterly", "mean"))
        .reset_index()
        .assign(
            population=lambda x: x["population"].round(), datasource_id=datasource.id
        )[["actor_id", "year", "population", "datasource_id"]]
    )

    population_validated = [
        Population(
            id=f"{row.actor_id}:{row.year}",
            year=row.year,
            actor_id=row.actor_id,
            population=int(row.population),
            datasource_id=row.datasource_id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Population.__tablename__,
        data=population_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
