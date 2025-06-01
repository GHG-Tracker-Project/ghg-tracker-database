from datetime import datetime
import os
from pathlib import Path

import pandas as pd

from models import Actor, DataSource, ActorType
from utils import write_csv


def main():
    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "iso-3166-1"
    publisher = "ipregistry"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="ISO-3166 data",
        publisher=publisher,
        published_date=datetime.strptime("2023-11-23", "%Y-%m-%d"),
        version="2023-11-23",
        url="https://github.com/ipregistry/iso3166",
    )

    # load data
    data_dir = Path(os.path.abspath(f"./data/{datasource_name}"))
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        output_dir=output_dir,
        name=datasource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # actor table
    # ------------------------------------------
    fl_countries = data_dir / "raw/countries.csv"
    fl_sovereignty = data_dir / "raw/countries-sovereignty.csv"

    df = (
        pd.read_csv(fl_countries, keep_default_na=False)
        .merge(
            pd.read_csv(fl_sovereignty, keep_default_na=False),
            left_on="#country_code_alpha2",
            right_on="#country_code",
        )
        .assign(
            type=lambda x: x.apply(
                lambda row: "country" if row["is_independent"] else "territory", axis=1
            )
        )
        .rename(
            columns={
                "#country_code": "id",
                "name_short": "name",
                "sovereign_country_code": "sovereign_code",
            }
        )
        .assign(is_part_of="")
        .assign(datasource_id=datasource.id)
        .assign(sovereign_code=lambda x: x["sovereign_code"].fillna(""))
        .drop_duplicates()
        .sort_values(by=["type", "id"])[
            ["id", "name", "is_part_of", "type", "sovereign_code", "datasource_id"]
        ]
    )

    # data validation
    actors_validated = [
        Actor(
            id=row.id,
            name=row.name,
            is_part_of=row.is_part_of,
            type=ActorType(row.type),
            sovereign_code=row.sovereign_code,
            datasource_id=row.datasource_id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir, name=Actor.__tablename__, data=actors_validated, mode="w"
    )

    return actors_validated


if __name__ == "__main__":
    df = main()
