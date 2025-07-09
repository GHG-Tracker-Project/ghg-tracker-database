from datetime import datetime
from pathlib import Path

import pandas as pd

from utils import write_csv

from models import DataSource, Sector


def main():
    # output directory
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "ipcc-crf"
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    fl = data_dir / "raw" / "crf_sector.xls"

    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "crf"
    publisher = "ipcc"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="CRF Sector Codes",
        publisher=publisher,
        published_date=datetime.strptime("2015-03-05", "%Y-%m-%d"),
        url="https://www.eea.europa.eu/ds_resolveuid/53da45821f2b96e930dfc6f47bcb8f59",
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
    df = (
        pd.read_excel(fl, sheet_name="CRF_sector", header=2)
        .rename(
            columns={
                "Sector code": "code",
                "Parent sector code": "parent_code",
                "Sector name": "name",
            }
        )
        .fillna("")
        .astype({"code": str, "parent_code": str, "name": str})
    )

    sector_validated = [
        Sector(
            id=f"crf:{row.code}",
            code=row.code,
            parent_code=row.parent_code,
            name=row.name,
            taxonomy="IPCC common reporting framework (CRF)",
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
