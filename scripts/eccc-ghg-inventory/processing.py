from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from utils import write_csv
from utils import display_excel_sheets

from models import (
    AssessmentReport,
    DataSource,
    GasType,
    Emissions,
    EmissionsCO2e,
    EmissionsTotalCO2e,
    EmissionsTotalSector,
    AggregationType,
)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def full_year(two_digit):
    year = int(two_digit)
    if year >= 50:
        return 1900 + year
    else:
        return 2000 + year


def main():
    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "official-ghg-inventory"
    publisher = "ECCC"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="Official Greenhouse Gas Inventory",
        publisher=publisher,
        published_date=datetime.strptime("2025-03-21", "%Y-%m-%d"),
        version="20250321",
        url="https://data.ec.gc.ca/data/substances/monitor/canada-s-official-greenhouse-gas-inventory/A-IPCC-Sector/?lang=en",
    )

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / "eccc-ghg-inventory"
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
    df_actors = df_actors.loc[df_actors["is_part_of"] == "CA", ["id"]].rename(
        columns={"id": "actor_id"}
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

    df_gwp = (
        pd.read_csv(fl_gwp)
        .loc[:, ["id", "gwp", "gas", "assessment_report"]]
        .rename(columns={"id": "gwp_id"})
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
    )

    # container to hold all the dataframes
    list_of_dfs = []

    files = (data_dir / "raw").glob("EN_GHG_IPCC_??.xlsx")

    for fl in files:
        actor_id = f"CA-{fl.stem[-2:]}"

        actor_is_valid = df_actors["actor_id"].isin([actor_id]).any()

        if not actor_is_valid:
            raise ValueError(f"Actor ID {actor_id} not found in df_actors.")

        sheets = display_excel_sheets(fl)
        sheets_that_are_years = [sheet for sheet in sheets if is_number(sheet)]

        for sheet_name in sheets_that_are_years:
            # sheet_name = "22"
            year = full_year(sheet_name)
            df_raw = pd.read_excel(fl, sheet_name=sheet_name, header=3)

            # get the want to end at
            idx = df_raw.index[df_raw["Unnamed: 0"] == "Notes:"].tolist()[0]

            df_tmp = (
                df_raw.rename(columns={"Unnamed: 0": "sector"})
                .loc[:, ["sector", "CO2", "CH4", "N2O", "HFCsa", "PFCsa", "SF6", "NF3"]]
                .rename(columns={"HFCsa": "HFCs", "PFCsa": "PFCs"})
                .loc[: (idx - 1)]
            )
            sectors = [
                "TOTALb",
                "ENERGY",
                "INDUSTRIAL PROCESSES AND PRODUCT USE",
                "AGRICULTURE",
                "WASTE",
                "LAND USE, LAND-USE CHANGE AND FORESTRY",
            ]
            all_gases = ["CO2", "CH4", "N2O", "HFCs", "PFCs", "SF6", "NF3"]
            F_gases = ["HFCs", "PFCs", "SF6", "NF3"]
            main_three = ["CO2", "CH4", "N2O"]

            # get units and gwps
            df_units = df_tmp[1:2].melt(
                value_vars=all_gases, id_vars=None, value_name="unit", var_name="gas"
            )

            df_data = (
                df_tmp.loc[2:, :]
                .melt(
                    value_vars=all_gases,
                    id_vars="sector",
                    value_name="emissions",
                    var_name="gas",
                )
                .dropna(subset=["emissions"])
                .query("sector.isin(@sectors)")
                .query('emissions != "-"')
            )
            fgases = ["HFCs", "PFCs", "NF3", "SF6"]
            main_gases = ["CO2", "CH4", "N2O"]

            # Make the FGASES totals by sector
            fgases_sum = (
                df_tmp.loc[2:, :]
                .melt(
                    value_vars=all_gases,
                    id_vars="sector",
                    value_name="emissions",
                    var_name="gas",
                )
                .dropna(subset=["emissions"])
                .query("sector.isin(@sectors)")
                .query('emissions != "-"')
                .query("gas in @fgases")
                .groupby("sector", as_index=False)
                .agg({"emissions": "sum"})
                .assign(gas="FGASES", units="kt CO2 / yr")
            )

            # Keep original CO2, CH4, N2O rows
            other_gases = (
                df_tmp.loc[2:, :]
                .melt(
                    value_vars=all_gases,
                    id_vars="sector",
                    value_name="emissions",
                    var_name="gas",
                )
                .dropna(subset=["emissions"])
                .query("sector.isin(@sectors)")
                .query('emissions != "-"')
                .query("gas in @main_gases")
                .assign(
                    units=lambda x: x.apply(
                        lambda row: f"kt {row['gas']} /year", axis=1
                    )
                )
            )

            # Concatenate back together
            df_data = (
                pd.concat([other_gases, fgases_sum], ignore_index=True)
                .sort_values(["sector", "gas"])
                .reset_index(drop=True)
                .rename(columns={"emissions": "emissions_kt"})
                .assign(actor_id=actor_id, year=year)
            )
            kt_to_tonne = 1_000

            df_sheet = (
                df_data.assign(
                    name_sanitized=lambda x: x.apply(
                        lambda row: row["sector"]
                        .replace("-", " ")
                        .replace(",", "")
                        .lower(),
                        axis=1,
                    )
                )
                .merge(
                    df_sector.loc[:, ["sector_id", "code", "name_sanitized"]],
                    on="name_sanitized",
                )
                .assign(
                    datasource_id=datasource.id,
                    assessment_report="AR5",
                    emissions_tonnes=lambda x: x["emissions_kt"] * kt_to_tonne,
                    units=lambda x: x["units"].str.replace("kt", "tonne", regex=False),
                )
                .astype({"emissions_tonnes": float})
                .merge(df_gwp, on=["gas", "assessment_report"], how="left")
                .assign(
                    emissions_tonnes_co2e=lambda x: np.round(
                        x["emissions_tonnes"] * x["gwp"], 11
                    ).fillna(x["emissions_tonnes"]),
                    gwp_id=lambda x: x["gwp_id"].fillna(""),
                    gwp=lambda x: x["gwp"].fillna(""),
                )
                .loc[
                    :,
                    [
                        "actor_id",
                        "year",
                        "sector_id",
                        "gas",
                        "gwp",
                        "gwp_id",
                        "emissions_tonnes",
                        "units",
                        "emissions_tonnes_co2e",
                        "assessment_report",
                        "datasource_id",
                    ],
                ]
            )

            list_of_dfs.append(df_sheet)

    # concatenate all the dataframes
    df = pd.concat(list_of_dfs)

    # ------------------------------------------
    # emissions
    # ------------------------------------------
    emissions_validated = [
        Emissions(
            id=f"{row.actor_id}:{row.year}:{row.gas}:{row.sector_id}",
            actor_id=row.actor_id,
            gas=GasType(row.gas),
            sector_id=row.sector_id,
            year=row.year,
            emissions=row.emissions_tonnes,
            units=row.units,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.query("gas.isin(@main_three)").itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Emissions.__tablename__,
        data=emissions_validated,
        mode="w",
    )

    # ------------------------------------------
    # emissions CO2eq
    # ------------------------------------------
    emissionsco2e_validated = [
        EmissionsCO2e(
            id=f"{row.actor_id}:{row.year}:{row.sector_id}:{row.gas}:{row.assessment_report}",
            actor_id=row.actor_id,
            sector_id=row.sector_id,
            gas=GasType(row.gas),
            gwp_id=row.gwp_id,
            assessment_report=AssessmentReport(row.assessment_report),
            year=row.year,
            emissions=row.emissions_tonnes_co2e,
            units="CO2 * tonne / yr",
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsCO2e.__tablename__,
        data=emissionsco2e_validated,
        mode="w",
    )

    gases_included = ", ".join(df["gas"].unique())
    df_total_sector = (
        df.groupby(["actor_id", "year", "sector_id", "assessment_report"])
        .sum("emissions_tonnes_co2e")
        .reset_index()
    )

    # ------------------------------------------
    # emissions total sector
    # ------------------------------------------
    emissionstotalsector_validated = [
        EmissionsTotalSector(
            id=f"{row.actor_id}:{row.year}:{row.sector_id}:{row.assessment_report}",
            actor_id=row.actor_id,
            sector_id=row.sector_id,
            year=row.year,
            emissions=row.emissions_tonnes_co2e,
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
        .sum("emissions_tonnes_co2e")
        .reset_index()
        .assign(aggregation_type="total")
    )

    df_total_ex_lulucf = (
        df_total_sector.query(
            "sector_id.isin(['crt:1','crt:2','crt:3','crt:5','crt:6'])"
        )  # excclude lulucf
        .groupby(["actor_id", "year", "assessment_report"])
        .sum("emissions_tonnes_co2e")
        .reset_index()
        .assign(aggregation_type="total_ex_lulucf")
    )

    df_emission_totals = pd.concat([df_total_all_sector, df_total_ex_lulucf]).drop(
        columns=["emissions_tonnes"]
    )

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
            emissions=row.emissions_tonnes_co2e,
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
