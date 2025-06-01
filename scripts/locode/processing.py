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
    datasource_name = "locode"
    publisher = "unece"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="United Nations Code for Trade and Transport Locations",
        publisher=publisher,
        published_date=datetime.strptime("2025-01-15", "%Y-%m-%d"),
        version="v2024-2",
        url="https://unece.org/trade/uncefact/unlocode",
    )

    # load data
    data_dir = Path(os.path.abspath(f"../data/{datasource_name}"))
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

    # column names and descriptions here: https://service.unece.org/trade/locode/Service/LocodeColumn.htm
    columns = [
        "Ch",
        "Locode",
        "Name",
        "NameWoDiacritics",
        "SubDiv",
        "Function",
        "Status",
        "Date",
        "IATA",
        "Coordinates",
        "Remarks",
    ]

    files = [
        data_dir / "raw/loc242csv/2024-2 UNLOCODE CodeListPart1.csv",
        data_dir / "raw/loc242csv/2024-2 UNLOCODE CodeListPart2.csv",
        data_dir / "raw/loc242csv/2024-2 UNLOCODE CodeListPart3.csv",
    ]

    df_actors = pd.concat(
        [
            pd.read_csv("../data/iso-3166-1/processed/actor.csv"),
            pd.read_csv("../data/iso-3166-2/processed/actor.csv"),
        ]
    )

    # this is a little cumbersome because it is long list comprehension
    # this could be improved
    df = pd.concat(
        [
            pd.read_csv(file, encoding="latin1", names=columns, keep_default_na=False)
            .reset_index(drop=True)
            .query("~Locode.eq('')")
            .loc[lambda x: x["Locode"].notnull()]
            .assign(id=lambda x: x["Ch"] + x["Locode"])
            .assign(
                is_part_of=lambda x: x.apply(
                    lambda row: row["Ch"] + "-" + row["SubDiv"]
                    if row["SubDiv"]
                    else row["Ch"],
                    axis=1,
                )
            )
            .query("is_part_of.isin(@df_actors['id'])")
            .assign(datasource_id=datasource.id)
            .assign(type="city")
            .rename(columns={"NameWoDiacritics": "name"})[
                ["id", "name", "is_part_of", "type", "datasource_id"]
            ]
            .drop_duplicates()
            .drop_duplicates(subset="id", keep="first")
            for file in files
        ]
    )

    # data validation
    actors_validated = [
        Actor(
            id=row.id,
            name=row.name,
            is_part_of=row.is_part_of,
            type=ActorType(row.type),
            datasource_id=row.datasource_id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir, name=Actor.__tablename__, data=actors_validated, mode="w"
    )

    return df


if __name__ == "__main__":
    df = main()
