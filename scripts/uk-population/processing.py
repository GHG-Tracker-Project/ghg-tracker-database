from datetime import datetime
from pathlib import Path

import pandas as pd

from models import DataSource, Population
from utils import write_csv


def main():
    # output directory
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "uk-population"
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "uk-population-estimates"
    publisher = "Office of National Statistics"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name=datasource_name,
        publisher=publisher,
        published_date=datetime.strptime("2024-07-15", "%Y-%m-%d"),
        version="MYE23",
        url="https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland",
    )

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # read data
    # ------------------------------------------
    fl = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "uk-population"
        / "raw"
        / "ukpopulationestimates183820231.xlsx"
    )

    df = pd.read_excel(fl, sheet_name="Contents")

    # ------------------------------------------
    # get actors
    # ------------------------------------------
    fl_actors = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "iso-3166-2"
        / "processed"
        / "actor.csv"
    )

    df_actors = pd.read_csv(fl_actors, keep_default_na=False)
    df_ids = (
        df_actors.query("is_part_of == 'GB'")
        .loc[:, ["id", "name"]]
        .rename(columns={"id": "actor_id"})
    )

    # ------------------------------------------
    # population table
    # ------------------------------------------
    mapping = {
        "England": "Table 10",
        "Wales": "Table 12",
        "Scotland": "Table 14",
        "Northern Ireland": "Table 17",
    }

    dfs = []
    for name, table in mapping.items():
        df_tmp = (
            pd.read_excel(fl, sheet_name=table, header=1)
            .assign(year=lambda d: d["Year"].str.extract(r"(\d{4})").astype(int))
            .rename(columns={"Persons": "population"})
            .assign(actor_id=str(df_ids.query("name == @name")["actor_id"].values[0]))
            .assign(
                population=lambda d: pd.to_numeric(d["population"], errors="coerce")
            )
            .loc[:, ["actor_id", "year", "population"]]
            .dropna()
        )
        dfs.append(df_tmp)

    df = (
        pd.concat(dfs)
        .sort_values(by=["actor_id", "year"])
        .astype({"actor_id": str, "year": int, "population": int})
    )

    population_validated = [
        Population(
            id=f"{row.actor_id}:{row.year}",
            year=row.year,
            actor_id=row.actor_id,
            population=row.population,
            datasource_id=datasource.id,
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
