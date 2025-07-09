from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from utils import write_csv
from models import (
    AssessmentReport,
    DataSource,
    GasType,
    EmissionsTotalCO2e,
    EmissionsTotalSector,
    AggregationType,
)


def main():

    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "official-ghg-inventory"
    publisher = "DCCEEW"

    # datasets and apis > Activity tables
    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="State & Territory Inventories 2023 - Emission Data Tables (Excel)",
        publisher=publisher,
        published_date=datetime.strptime("2025-05-01", "%Y-%m-%d"),
        version="20250501",
        url="https://www.greenhouseaccounts.climatechange.gov.au/",
    )

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / "au-state-emissions"
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
    df_actors = df_actors.loc[df_actors["is_part_of"] == "AU", ["id", "name"]].rename(
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
    # load raw_data
    # ------------------------------------------

    fl = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "au-state-emissions"
        / "raw"
        / "state-territory-inventories-2023-emission-data-tables.xlsx"
    )

    sheets = [
        "NSW",
        "Qld",
        "Vic",
        "WA",
        "SA",
        "NT",
        "Tas",
        "ACT",
    ]

    list_of_dfs = []

    # loop over sheets
    for sheet in sheets:
        # sheet = "Vic"
        actor_id = f"AU-{sheet.upper()}"

        # if not actor_id in list(df_actors["actor_id"]):
        df_tmp = pd.read_excel(fl, sheet_name=sheet, header=6)
        sectors = [
            "1. Energy",
            "2.  Industrial Processes",
            "3.  Agriculture",
            "4. Land Use, Land-Use Change and Forestry",
            "5.  Waste",
        ]
        Gg_to_tonne = 1_000
        df_sheet = (
            df_tmp.loc[
                df_tmp["IPCC emissions source and sink categories"].isin(sectors)
            ]
            .rename(
                columns=lambda col: (
                    re.match(r"^\d{4}", col).group(0)
                    if re.match(r"^\d{4}", col)
                    else col
                )
            )
            .rename(columns={"IPCC emissions source and sink categories": "sector"})
            .drop(columns=df_tmp.columns[df_tmp.columns.str.startswith("Change from")])
            .pipe(
                lambda d: d.melt(
                    id_vars="sector",
                    value_vars=[col for col in d.columns if col.isdigit()],
                    var_name="year",
                    value_name="emissions_Gg",
                )
            )
            .assign(
                code=lambda x: x["sector"].str.extract(r"^(\d+)"),
                sector=lambda x: x["sector"].str.replace(r"^\d+\.\s*", "", regex=True),
            )
            .merge(df_sector, on="code")
            .assign(
                actor_id=actor_id,
                assessment_report="AR5",
                emissions=lambda x: x["emissions_Gg"] * Gg_to_tonne,
                units="CO2 tonne / year",
            )
            # .assign(sector=lambda x: x['sector'].str.replace(r"^\d+\.\s*", "", regex=True))
        )

        list_of_dfs.append(df_sheet)

    df = pd.concat(list_of_dfs).astype({"year": int})

    # ------------------------------------------
    # emissions total sector
    # ------------------------------------------

    gases_included = ""

    # using .agg({"emissions": "sum"}) is safer than .sum("emissions")
    # works for singular values, unline .sum
    df_total_sector = (
        df.groupby(["actor_id", "year", "sector_id", "assessment_report"])
        .agg({"emissions": "sum"})
        .reset_index()
    )

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
        for row in df_total_sector.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalSector.__tablename__,
        data=emissionstotalsector_validated,
        mode="w",
    )

    df_total_all_sector = (
        df_total_sector.query(
            "sector_id.isin(['crt:1','crt:2','crt:3','crt:4','crt:5','crt:6'])"
        )  # all sectors
        .groupby(["actor_id", "year", "assessment_report"])
        .agg({"emissions": "sum"})
        .reset_index()
        .assign(aggregation_type="total")
    )

    df_total_ex_lulucf = (
        df_total_sector.query(
            "sector_id.isin(['crt:1','crt:2','crt:3','crt:5','crt:6'])"
        )  # excclude lulucf
        .groupby(["actor_id", "year", "assessment_report"])
        .agg({"emissions": "sum"})
        .reset_index()
        .assign(aggregation_type="total_ex_lulucf")
    )

    df_emission_totals = pd.concat([df_total_all_sector, df_total_ex_lulucf])

    # ------------------------------------------
    # emission total
    # sum across all sector and gases
    # total and excluding lulucf
    # ------------------------------------------
    # total across sector and gas
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
