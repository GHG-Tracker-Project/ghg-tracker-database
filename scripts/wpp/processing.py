from datetime import datetime
from pathlib import Path

import pandas as pd

from models import DataSource, Population
from utils import write_csv


# these are not in WPP, which is fine
# but maybe we should remove them from our actors table?
# are they necessary?

# 'AQ', # antarctica
# 'AX', # Åland Islands
# 'BV', # Bouvet Island (uninhabitated)
# 'CC', # COCOS (KEELING) ISLANDS
# 'CX', # Christmas Island (could be removed)?
# 'GS', # South Georgia and the South Sandwich Islands
# 'HM', #  Heard Island and McDonald Islands
# 'IO', # British Indian Ocean Territory
# 'NF', # Norfolk Island
# 'PN', # Pitcairn islands
# 'SJ', # Svalbard and Jan Mayen
# 'TF', # French Southern and Antarctic Lands
# 'UM', # United States Minor Outlying Islands (the)

# This one is in WPP, but not the ISO database
# should we make a Kosovo record?
# {'XK'}


def main():

    # define  datasource and publisher at top
    # datasource used to make data directory
    datasource_name = "wpp"
    publisher = "United Nations"

    # load data

    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource = DataSource(
        id=f"{publisher.replace(" ","_")}:{datasource_name}",
        name="World Population Prospects 2024",
        publisher=publisher,
        published_date=datetime.strptime("2024-01-01", "%Y-%m-%d"),
        version="2024",
        url="https://population.un.org/wpp/downloads?folder=Standard%20Projections&group=CSV%20format",
    )

    write_csv(
        output_dir=output_dir,
        name=datasource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # get all country codes
    # ------------------------------------------
    actors_csv_file = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "iso-3166-1"
        / "processed"
        / "actor.csv"
    )
    df_actors = pd.read_csv(actors_csv_file)
    df_actors_ids = df_actors["id"]  # noqa: F841

    # ------------------------------------------
    # population table
    # ------------------------------------------
    fl = data_dir / "raw" / "WPP2024_TotalPopulationBySex.csv"

    columns = [
        "ISO3_code",
        "ISO2_code",
        "LocTypeName",
        "ParentID",
        "Location",
        "Variant",
        "Time",
        "PopTotal",
        "PopDensity",
    ]

    # low_memory is appease this warning:
    # DtypeWarning: Columns (2,3,4,7) have mixed types. Specify dtype option on import or set low_memory=False.
    df = (
        pd.read_csv(fl, low_memory=False)
        .loc[:, columns]
        .query("ISO2_code.notnull()")
        .query("ISO2_code.isin(@df_actors_ids)")
        .query("Variant == 'Medium'")
        .query("Time <= 2025")  # note last two years are a projection
        .rename(columns={"ISO2_code": "actor_id", "Time": "year"})
        .assign(
            population=lambda x: x.apply(lambda row: row["PopTotal"] * 1000, axis=1)
        )
        .loc[:, ["actor_id", "year", "population"]]
        .astype({"actor_id": str, "year": int, "population": int})
    )

    populations_validated = [
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
        data=populations_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
