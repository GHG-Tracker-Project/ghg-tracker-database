from datetime import datetime
from pathlib import Path

import pandas as pd

from utils import write_csv
from models import DataSource, Sector


def main():
    # output directory
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "crt-on-nir"
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    fl = data_dir / "raw" / "crt.xls"

    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "crt"
    publisher = "ipcc"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="Common Reporting Tables (CRT) on NIRS",
        publisher=publisher,
        published_date=datetime.strptime("2015-03-05", "%Y-%m-%d"),
        url="https://unfccc.int/documents/311076",
    )

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # Sector table
    # ------------------------------------------
    fl = data_dir / "raw" / "crt.xlsx"

    df = pd.read_excel(fl, sheet_name="Summary1", header=9).loc[
        lambda x: x["Total national emissions and removals"].str.match(r"^\d", na=False)
    ]

    df[["code", "name"]] = df["Total national emissions and removals"].str.split(
        n=1, expand=True
    )
    df["code"] = df["code"].str.rstrip(".")
    df["parent_code"] = df["code"].str.extract(r"^(.*)\.[^.]+$")[0]
    df["name"] = df["name"].str.rstrip()
    df["name"] = (
        df["name"].str.replace(r"(?:\s*\([^)]+\))+$", "", regex=True).str.strip()
    )

    df = df.fillna("").astype({"code": str, "parent_code": str, "name": str})

    sector_validated = [
        Sector(
            id=f"crt:{row.code}",
            code=row.code,
            parent_code=row.parent_code,
            name=row.name,
            taxonomy="Common Reporting Table (CRT)",
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Sector.__tablename__,
        data=sector_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
