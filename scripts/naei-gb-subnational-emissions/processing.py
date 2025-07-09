"""
this is old, need to update to latest, version
"""

from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from utils import write_csv
from models import (
    AssessmentReport,
    DataSource,
    GasType,
    EmissionsCO2e,
    EmissionsTotalCO2e,
    EmissionsTotalSector,
    AggregationType,
)


def main():
    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "ghg-inventory-england-scotland-wales-northern-ireland-1990-2023"
    publisher = "NAEI"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="Greenhouse Gas Inventories for England, Scotland, Wales & Northern Ireland: 1990-2023",
        publisher=publisher,
        published_date=datetime.strptime("2025-10-06", "%Y-%m-%d"),
        version="20251006",
        url="https://naei.energysecurity.gov.uk/reports/greenhouse-gas-inventories-england-scotland-wales-northern-ireland-1990-2023",
    )

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "naei-gb-subnational-emissions"
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
    df_actors = df_actors.loc[df_actors["is_part_of"] == "GB", ["id", "name"]].rename(
        columns={"id": "actor_id"}
    )

    # ------------------------------------------
    # get sectors
    # ------------------------------------------
    fl_sector = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "crt-on-nir"
        / "processed"
        / "sector.csv"
    )
    df_sector_tmp = pd.read_csv(fl_sector)
    df_sector = (
        df_sector_tmp.query("code.isin(['0','1','2','3','4','5','6'])")
        .assign(
            name_sanitized=lambda x: x.apply(
                lambda row: row["name"].replace("-", " ").replace(",", "").lower(),
                axis=1,
            )
        )
        .rename(columns={"id": "sector_id"})
        .loc[:, ["sector_id", "code", "name"]]
    )

    # ------------------------------------------
    # get gwps
    # ------------------------------------------
    fl_gwp = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "gwp"
        / "processed"
        / "gwp.csv"
    )

    df_gwp = pd.read_csv(fl_gwp)

    # ------------------------------------------
    # load raw data
    # ------------------------------------------
    fl = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "naei-gb-subnational-emissions"
        / "raw"
        / "2209201114_DA_GHGI_1990-2020_Final_v4.1_AR4_AR5.xlsm"
    )

    sheets = [
        "England By Source_AR4",
        "England By Source_AR5",
        "Scotland By Source_AR4",
        "Scotland By Source_AR5",
        "Wales By Source_AR4",
        "Wales By Source_AR5",
        "Northern Ireland By Source_AR4",
        "Northern Ireland By Source_AR5",
    ]

    list_of_dfs = []

    for sheet in sheets:
        country = sheet.split("By")[0].strip()
        actor_id = df_actors.loc[df_actors["name"] == country, "actor_id"].to_list()[0]
        assessment_report = sheet.split("_")[-1]

        df_tmp = pd.read_excel(fl, sheet_name=sheet, header=16)

        years = [col for col in df_tmp.columns if str(col).isdigit()]
        kt_to_tonne = 1_000
        # row["IPCC_name"][0] if isinstance(row["IPCC_name"], str) else None

        df_sheet = (
            df_tmp.dropna(subset=["IPCC_name"])
            .drop(columns=["Unnamed: 0", "NCFormat", "BaseYear"])
            .assign(code=lambda x: x.apply(lambda row: row["IPCC_name"][0], axis=1))
            .melt(
                id_vars=["IPCC_name", "code"],
                value_vars=years,
                value_name="emissions_kt",
                var_name="year",
            )
            .merge(df_sector, on="code")
            .assign(
                actor_id=actor_id,
                assessment_report=assessment_report,
                emissions=lambda x: x.apply(
                    lambda row: row["emissions_kt"] * kt_to_tonne, axis=1
                ),
                units="CO2 tonne / year",
            )
            .groupby(
                ["code", "sector_id", "year", "assessment_report", "units", "actor_id"]
            )
            .sum("emissions")
            .reset_index()
        )

        list_of_dfs.append(df_sheet)

    df = pd.concat(list_of_dfs).astype({"year": int})

    gases_included = "CO2, CH4, N2O, FGASES"

    # ------------------------------------------
    # emissions total sector
    # ------------------------------------------
    emissionstotalsector_validated = [
        EmissionsTotalSector(
            id=f"{row.actor_id}:{row.year}:{row.sector_id}:{row.assessment_report}",
            actor_id=row.actor_id,
            sector_id=row.sector_id,
            year=row.year,
            emissions=row.emissions,
            gases_included=gases_included,
            assessment_report=AssessmentReport(row.assessment_report),
            units="CO2 * tonne / yr",
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalSector.__tablename__,
        data=emissionstotalsector_validated,
        mode="w",
    )

    # ------------------------------------------
    # emission total
    # sum across all sector and gases
    # total and excluding lulucf
    # ------------------------------------------
    # total across sector and gas

    df_total_all_sector = (
        df.query(
            "sector_id.isin(['crt:1','crt:2','crt:3','crt:4','crt:5','crt:6'])"
        )  # all sectors
        .groupby(["actor_id", "year", "assessment_report"])
        .sum("emissions")
        .reset_index()
        .assign(aggregation_type="total")
    )

    df_total_ex_lulucf = (
        df.query(
            "sector_id.isin(['crt:1','crt:2','crt:3','crt:5','crt:6'])"
        )  # excclude lulucf
        .groupby(["actor_id", "year", "assessment_report"])
        .sum("emissions")
        .reset_index()
        .assign(aggregation_type="total_ex_lulucf")
    )

    df_emission_totals = pd.concat([df_total_all_sector, df_total_ex_lulucf])

    emissionstotalco2e_validated = [
        EmissionsTotalCO2e(
            id=f"{row.actor_id}:{row.year}:{row.assessment_report}:{row.aggregation_type}",
            actor_id=row.actor_id,
            year=row.year,
            emissions=row.emissions,
            aggregation_type=AggregationType(row.aggregation_type),
            gases_included=gases_included,
            units="CO2 * tonne / yr",
            assessment_report=AssessmentReport(row.assessment_report),
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_emission_totals.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalCO2e.__tablename__,
        data=emissionstotalco2e_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
