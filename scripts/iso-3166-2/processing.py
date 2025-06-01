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
    datasource_name = "iso-3166-2"
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
    fl = data_dir / "raw/subdivisions.csv"

    df = (
        pd.read_csv(fl, keep_default_na=False)
        .assign(
            type=lambda x: x.apply(
                lambda row: "adm2" if row["parent_subdivision"] else "adm1", axis=1
            )
        )
        .assign(
            is_part_of=lambda x: x.apply(
                lambda row: row["parent_subdivision"]
                if row["parent_subdivision"]
                else row["#country_code_alpha2"],
                axis=1,
            )
        )
        .rename(
            columns={"subdivision_code_iso3166-2": "id", "subdivision_name": "name"}
        )
        .assign(datasource_id=datasource.id)
        .sort_values(by=["type", "id"])[
            ["id", "name", "is_part_of", "type", "datasource_id"]
        ]
        .drop_duplicates()
        .drop_duplicates(subset="id", keep="first")
    )

    # === Manual topological sort ===
    # solves the dependency problem
    # code is from LLM and I do not fully understand it. (not good)

    id_map = df.set_index("id")
    visited = set()
    ordered_ids = []

    def visit(node):
        if node in visited or node not in id_map.index:
            return
        parent = id_map.at[node, "is_part_of"]
        if parent and parent in id_map.index:
            visit(parent)
        visited.add(node)
        ordered_ids.append(node)

    for node in id_map.index:
        visit(node)

    # Apply the sorted order
    df = id_map.loc[ordered_ids].reset_index()

    # === End Manual topological sort ===

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
