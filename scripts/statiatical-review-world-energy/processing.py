from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from models import DataSource, EnergyConsumption
from utils import write_csv


def main():
    # output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "statistical-review-world-energy"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "Statistical review of world energy"
    publisher = "Energy Institute"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name=datasource_name,
        publisher=publisher,
        published_date=datetime.strptime("2025-01-1", "%Y-%m-%d"),
        version="74th edition",
        url="https://www.energyinst.org/statistical-review/resources-and-data-downloads",
    )

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # get actors
    # ------------------------------------------

    fl_actors = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "iso-3166-1"
        / "raw"
        / "countries.csv"
    )

    df_actors = pd.read_csv(fl_actors, keep_default_na=False)[
        ["#country_code_alpha2", "country_code_alpha3"]
    ].rename(
        columns={"#country_code_alpha2": "actor_id", "country_code_alpha3": "iso3"}
    )

    # ------------------------------------------
    # load data
    # ------------------------------------------

    fl_data = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "statistical-review-world-energy"
        / "raw"
        / "Statistical Review of World Energy Narrow File"
    )

    fl_glossary = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "statistical-review-world-energy"
        / "raw"
        / "Glossary.xlsx"
    )

    mapping = {
        "Coal": "fossil",
        "Gas": "fossil",
        "Oil": "fossil",
        "Solar": "renewable",
        "Wind": "renewable",
        "biofuels": "renewable",
        "biodiesel": "renewable",
        "Hydro": "renewable",
        "Nuclear": "nuclear",
    }
    df_data = pd.read_csv(fl_data)
    df_gloss = pd.read_excel(fl_glossary)

    # ------------------------------------------
    # EnergyConsumption table
    # ------------------------------------------

    columns = ["actor_id", "year", "consumption", "units", "fuel_type", "energy_source"]

    df = (
        df_data.merge(df_gloss, left_on="Var", right_on="Code")
        .loc[lambda x: x["Variable"].str.contains("consumption", case=False, na=False)]
        .query("Units.isin(['Exajoules', 'Petajoules'])")
        .merge(df_actors, left_on="ISO3166_alpha3", right_on="iso3")
        .rename(columns={"Year": "year", "Value": "consumption", "Units": "units"})
        .assign(
            fuel_type=lambda x: x["Variable"]
            .str.extract(r"^(.*?)\s*consumption", flags=re.IGNORECASE)[0]
            .str.strip()
        )
        .assign(energy_source=lambda x: x["fuel_type"].map(mapping))
        .loc[:, columns]
        .dropna()
    )
    consumption_validated = [
        EnergyConsumption(
            id=f"{row.actor_id}:{row.year}:{row.fuel_type}",
            year=row.year,
            actor_id=row.actor_id,
            consumption=row.consumption,
            units=row.units,
            fuel_type=row.fuel_type,
            energy_source=row.energy_source,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EnergyConsumption.__tablename__,
        data=consumption_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
