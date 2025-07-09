from datetime import datetime
from pathlib import Path
import re

import numpy as np
import pandas as pd
import xarray as xr


from models import (
    AggregationType,
    AssessmentReport,
    DataSource,
    Emissions,
    GasType,
    EmissionsCO2e,
    EmissionsTotalCO2e,
    EmissionsTotalSector,
)

from utils import write_csv


# need to fix round off error issue
# think need to Decimal instead of simply converting to float


def main():
    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "primap"
    publisher = "Climate Resource"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name=datasource_name,
        publisher=publisher,
        published_date=datetime.strptime("2025-03-13", "%Y-%m-%d"),
        version="2.6.1",
        url="https://zenodo.org/records/15016289",
    )

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
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
    df_sector = df_sector_tmp.query("code.isin(['0','1','2','3','4','5','6'])")

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

    # don't think I need this?
    # df_cats = (
    #    pd.read_csv(data_dir / "raw" / "emissions_categories.csv")
    #    .rename(columns={"Code":"code","Description":"description", "Gases covered":"gases_covered"})
    # )

    # ------------------------------------------
    # load raw data and metadata
    # ------------------------------------------
    fl = (
        data_dir
        / "raw"
        / "Guetschow_et_al_2025-PRIMAP-hist_v2.6.1_final_no_extrap_no_rounding_13-Mar-2025.nc"
    )
    ds = xr.open_dataset(fl).sel({"scenario (PRIMAP-hist)": "HISTTP"})

    # Create a metadata lookup table
    df_meta = pd.DataFrame(
        {
            "gas": list(ds.data_vars),
            "units": [ds[v].attrs.get("units") for v in ds.data_vars],
            "entity": [ds[v].attrs.get("entity") for v in ds.data_vars],
        }
    )
    # ------------------------------------------
    # make the main clean dataset
    # ------------------------------------------

    id_vars = [
        "time",
        "category (IPCC2006_PRIMAP)",
        "area (ISO3)",
        "scenario (PRIMAP-hist)",
    ]

    # FGASES: HFCs, PFCs, SF6, NF3
    gases = [
        "CO2",
        "CH4",
        "N2O",
        "FGASES (AR4GWP100)",
        "FGASES (AR5GWP100)",
        "FGASES (AR6GWP100)",
        "FGASES (SARGWP100)",
    ]

    gases_to_drop = [
        "NF3",
        "SF6",
        "HFCS (AR4GWP100)",
        "HFCS (AR5GWP100)",
        "HFCS (AR6GWP100)",
        "HFCS (SARGWP100)",
        "KYOTOGHG (AR4GWP100)",
        "KYOTOGHG (AR5GWP100)",
        "KYOTOGHG (AR6GWP100)",
        "KYOTOGHG (SARGWP100)",
        "PFCS (AR4GWP100)",
        "PFCS (AR5GWP100)",
        "PFCS (AR6GWP100)",
        "PFCS (SARGWP100)",
    ]

    # this is used in a .query() statement, it is being used
    codes = ["1", "2", "M.AG", "M.LULUCF", "4", "5"]

    primap_to_crt = {
        "1": "1",
        "2": "2",
        "M.AG": "3",
        "M.LULUCF": "4",
        "4": "5",
        "5": "6",
    }

    # Extract gas_split and assessment_report
    def split_gas_info(gas_str):
        match = re.match(r"(.+?) \((.+?)\)", gas_str)
        if match:
            gas_split = match.group(1)
            report_full = match.group(2)
            assessment_report = (
                "AR2" if report_full.startswith("SAR") else report_full[:3]
            )
            return pd.Series([gas_str, gas_split, assessment_report])
        return pd.Series([gas_str, gas_str, None])

    df_gas_data = (
        ds.to_dataframe()
        .reset_index()
        .melt(
            id_vars=id_vars, value_vars=gases, var_name="gas", value_name="emissions"
        )["gas"]
        .drop_duplicates()
        .apply(split_gas_info)
        .rename(columns={0: "gas", 1: "gas_split", 2: "assessment_report"})
    )

    gigagram_to_tonne = 1000

    # clean dataset, can fill emissions table using this
    df = (
        ds.to_dataframe()
        .reset_index()
        .drop(columns=["source", "provenance"])
        .drop(columns=gases_to_drop)
        .melt(id_vars=id_vars, value_vars=gases, var_name="gas", value_name="emissions")
        .rename(
            columns={
                "category (IPCC2006_PRIMAP)": "code",
                "area (ISO3)": "iso3",
                "scenario (PRIMAP-hist)": "scenario",
                "Description": "description",
                "Gases covered": "gases_covered",
            }
        )
        .dropna(subset=["emissions"])
        .query("emissions != 0")
        .query("code.isin(@codes)")
        .merge(df_meta, on="gas")
        .merge(df_actors, on="iso3")
        .assign(
            year=lambda x: x["time"].dt.year,
            code=lambda x: x["code"].apply(lambda c: primap_to_crt.get(c, None)),
        )
        .query("year>=1850")  # data actually goes back to 1750
        .merge(
            df_gwp.loc[:, ["id", "gwp", "gas", "assessment_report"]].rename(
                columns={"id": "gwp_id"}
            ),
            left_on="entity",
            right_on="gas",
            how="left",
        )
        .assign(gwp=lambda x: x["gwp"].fillna(1))
        .merge(df_gas_data, left_on="gas_x", right_on="gas")
        .assign(
            assessment_report=lambda x: x["assessment_report_x"].combine_first(
                x["assessment_report_y"]
            )
        )
        .loc[
            :,
            [
                "actor_id",
                "code",
                "year",
                "emissions",
                "units",
                "entity",
                "gwp",
                "gwp_id",
                "assessment_report",
            ],
        ]
        .rename(
            columns={
                "entity": "gas",
                "emissions": "emissions_gigagram",
                "code": "sector_code",
            }
        )
        .assign(
            emissions_tonnes=lambda x: np.round(
                x["emissions_gigagram"] * gigagram_to_tonne, 11
            ),
            units_tonnes=lambda x: x["units"].str.replace(
                "gigagram", "tonne", regex=False
            ),
        )
        .assign(
            emissions_tonnes_co2e=lambda x: np.round(
                x["emissions_tonnes"] * x["gwp"], 11
            ),
            gwp_id=lambda x: x["gwp_id"].fillna(""),
        )
        .merge(
            df_sector.loc[:, ["id", "code", "name", "taxonomy"]].rename(
                columns={
                    "id": "sector_id",
                    "code": "sector_code",
                    "name": "sector_name",
                }
            ),
            on="sector_code",
        )
    )

    # ------------------------------------------
    # emissiosns dataset for gases in natural units
    # ------------------------------------------
    # CO2, CH4, and N2O only
    # ToDo: drop_duplicates() here is a really a monkey patch
    # i have duplicates becuase I have values for all the assessment reports
    # which means the raw emissions are duplicated.
    # should handle this more elegantly
    df_emissions = (
        df.query("gas.isin(['CO2', 'CH4', 'N2O'])")
        .loc[
            :,
            [
                "actor_id",
                "year",
                "gas",
                "sector_id",
                "emissions_tonnes",
                "units_tonnes",
            ],
        ]
        .drop_duplicates()
    )

    emissions_validated = [
        Emissions(
            id=f"{row.actor_id}:{row.year}:{row.gas}:{row.sector_id}",
            actor_id=row.actor_id,
            gas=GasType(row.gas),
            sector_id=row.sector_id,
            year=row.year,
            emissions=row.emissions_tonnes,
            units=row.units_tonnes,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_emissions.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Emissions.__tablename__,
        data=emissions_validated,
        mode="w",
    )

    # ------------------------------------------
    # emissions in co2e units
    # includes all the gases, including FGASES
    # ------------------------------------------
    # all gases in co2e, breakdown into sector and gas
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

    # ------------------------------------------
    # emissionTotalSector
    # ------------------------------------------
    gases_included = ", ".join(list(df["gas"].unique()))
    df_emissions_total_sector = (
        df.loc[
            :,
            [
                "actor_id",
                "sector_id",
                "year",
                "assessment_report",
                "emissions_tonnes_co2e",
                "gas",
            ],
        ]
        .groupby(["actor_id", "year", "assessment_report", "sector_id"])
        .sum("emissions_tonnes_co2e")
        .reset_index()
    )

    # sum across gas
    # include
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
        for row in df_emissions_total_sector.itertuples()
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
    df_emissions_total = (
        df.loc[
            :,
            [
                "actor_id",
                "sector_id",
                "sector_code",
                "year",
                "assessment_report",
                "emissions_tonnes_co2e",
                "gas",
            ],
        ]
        .query("gas.isin(['CO2', 'CH4', 'N2O', 'FGASES'])")  # all gases
        .query("sector_code.isin(['1','2','3','4','5','6'])")  # all sectors
        .groupby(["actor_id", "year", "assessment_report"])
        .sum("emissions_tonnes_co2e")
        .reset_index()
        .assign(aggregation_type="total")
    )

    df_emissions_total_el = (
        df.loc[
            :,
            [
                "actor_id",
                "sector_id",
                "sector_code",
                "year",
                "assessment_report",
                "emissions_tonnes_co2e",
                "gas",
            ],
        ]
        .query("gas.isin(['CO2', 'CH4', 'N2O', 'FGASES'])")  # all gases
        .query("sector_code.isin(['1','2','3', '5','6'])")  # excludes LULUCF
        .groupby(["actor_id", "year", "assessment_report"])
        .sum("emissions_tonnes_co2e")
        .reset_index()
        .assign(aggregation_type="total_ex_lulucf")
    )

    df_emissions_total = pd.concat([df_emissions_total, df_emissions_total_el])
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
        for row in df_emissions_total.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalCO2e.__tablename__,
        data=emissionstotalco2e_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
