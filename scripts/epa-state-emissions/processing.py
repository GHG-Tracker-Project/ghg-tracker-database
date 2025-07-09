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
    datasource_name = "state-ghg-emissions-and-removals"
    publisher = "EPA"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="State GHG Emissions and Removals",
        publisher=publisher,
        published_date=datetime.strptime("2024-08-29", "%Y-%m-%d"),
        version="v082924",
        url="https://www.epa.gov/ghgemissions/state-ghg-emissions-and-removals",
    )

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / "epa-state-emissions"
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
    df_actors = df_actors.loc[df_actors["is_part_of"] == "US", ["id"]].rename(
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
    # load raw data and process
    # ------------------------------------------
    fl = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "epa-state-emissions"
        / "raw"
        / "allstateghgdata90-22_v082924"
        / "AllStateGHGData90-22_v082924.xlsx"
    )

    id_vars = [
        "sector",
        "subsector",
        "category",
        "sub_category_1",
        "sub_category_2",
        "sub_category_3",
        "sub_category_4",
        "sub_category_5",
        "carbon_pool",
        "fuel1",
        "fuel2",
        "geo_ref",
        "units",
        "ghg_category",
        "ghg",
        "gwp",
    ]

    value_vars = [str(num) for num in range(1990, 2023)]

    geo_refs_to_drop = [
        "USTERR",  # aggregated emissions from US territories
        "FO",  # emissions occurring offshore within US water
        "National",  # emissions and sinks not disaggregated
    ]

    # filt = ~df["STATE"].isin(drop_s#tates)

    Tg_to_tonne = 1_000_000

    cofa_states = ["FM", "MH", "PW"]  # micronesia, marshall islands, palau
    us_territories = ["AS", "GU", "MP", "PR", "UM", "VI"]

    df_co2_ch4_n2o = (
        pd.read_excel(fl, sheet_name="Data by UNFCCC-IPCC Sectors")
        .query("not geo_ref.isin(@geo_refs_to_drop)")
        .query("not geo_ref.isin(@cofa_states)")
        .query("not geo_ref.isin(@us_territories)")
        .query("ghg_category.isin(['CO2', 'CH4', 'N2O'])")
        .rename(
            columns=lambda x: re.sub(r"^Y(\d{4})", r"\1", x)
        )  # regex to remove leading Y from years
        .melt(
            id_vars=id_vars,
            value_vars=value_vars,
            value_name="emissions",
            var_name="year",
        )
        .drop(columns=["sub_category_4", "sub_category_5"])
        .groupby(["sector", "geo_ref", "year", "ghg_category", "units", "gwp"])
        .sum("emissions")
        .reset_index()
        .assign(
            datasource_id=datasource.id,
            assessment_report="AR5",
            emissions_tonnes=lambda x: x["emissions"] * Tg_to_tonne,
            units="CO2 tonnes / yr",
            actor_id=lambda x: x.apply(lambda row: f"US-{row.geo_ref}", axis=1),
        )
        .rename(columns={"emissions": "emissions_Tg"})
    )

    df_fgases = (
        pd.read_excel(fl, sheet_name="Data by UNFCCC-IPCC Sectors")
        .query("not geo_ref.isin(@geo_refs_to_drop)")
        .query("not geo_ref.isin(@cofa_states)")
        .query("not geo_ref.isin(@us_territories)")
        .query("ghg_category.isin(['HFC', 'NF3', 'PFC', 'SF6'])")
        .rename(
            columns=lambda x: re.sub(r"^Y(\d{4})", r"\1", x)
        )  # regex to remove leading Y from years
        .melt(
            id_vars=id_vars,
            value_vars=value_vars,
            value_name="emissions",
            var_name="year",
        )
        .drop(columns=["sub_category_4", "sub_category_5"])
        .groupby(["sector", "geo_ref", "year", "units"])
        .sum("emissions")
        .reset_index()
        .assign(datasource_id=datasource.id)
        .assign(
            gwp="",  # or put one here?
            ghg_category="FGASES",
            assessment_report="AR5",
            emissions_tonnes=lambda x: x["emissions"] * Tg_to_tonne,
            units="CO2 tonne / yr",
            actor_id=lambda x: x.apply(lambda row: f"US-{row.geo_ref}", axis=1),
        )
        .rename(columns={"emissions": "emissions_Tg"})
    )

    unique_gwp = (
        df_co2_ch4_n2o.rename(columns={"ghg_category": "gas"})
        .loc[:, ["gwp", "assessment_report", "gas"]]
        .loc[lambda x: x["gwp"] != ""]
        .astype({"gwp": float})
        .drop_duplicates()
    )

    gwp_data = unique_gwp.merge(
        df_gwp[["id", "gwp", "assessment_report", "gas"]].rename(
            columns={"id": "gwp_id"}
        ),
        on=["gwp", "assessment_report", "gas"],
    ).astype({"gwp": object})

    df = (
        pd.concat([df_co2_ch4_n2o, df_fgases])
        .assign(
            name_sanitized=lambda x: x.apply(
                lambda row: row["sector"].replace("-", " ").replace(",", "").lower(),
                axis=1,
            )
        )
        .merge(
            df_sector.loc[:, ["sector_id", "code", "taxonomy", "name_sanitized"]],
            on="name_sanitized",
        )
        .rename(columns={"ghg_category": "gas"})
        .loc[
            :,
            [
                "actor_id",
                "year",
                "gas",
                "gwp",
                "emissions_tonnes",
                "units",
                "datasource_id",
                "sector_id",
                "assessment_report",
            ],
        ]
        .merge(gwp_data, on=["gwp", "assessment_report", "gas"], how="left")
        .assign(gwp_id=lambda x: x["gwp_id"].fillna(""))
        .astype({"year": int})
    )

    # ------------------------------------------
    # emissions CO2e
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
            emissions=row.emissions_tonnes,
            units=row.units,
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
    # emissions total sector
    # ------------------------------------------
    df_totalsector = (
        df.groupby(["actor_id", "year", "sector_id", "assessment_report"])
        .sum("emissions_tonnes")
        .reset_index()
    )
    gases_included = ", ".join(df["gas"].unique())

    # finish this
    emissionstotalsector_validated = [
        EmissionsTotalSector(
            id=f"{row.actor_id}:{row.year}:{row.sector_id}:{row.assessment_report}",
            actor_id=row.actor_id,
            sector_id=row.sector_id,
            year=row.year,
            emissions=row.emissions_tonnes,
            units="CO2 tonnes / yr",
            gases_included=gases_included,
            assessment_report=AssessmentReport(row.assessment_report),
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_totalsector.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalSector.__tablename__,
        data=emissionstotalsector_validated,
        mode="w",
    )

    # ------------------------------------------
    # emissions total aggregated
    # ------------------------------------------

    df_total = (
        df.groupby(["actor_id", "year", "assessment_report"])
        .sum("emissions_tonnes")
        .reset_index()
        .assign(aggregation_type="total")
    )

    df_total_ex_lulucf = (
        df.query("not sector_id.isin(['crt:4'])")
        .groupby(["actor_id", "year", "assessment_report"])
        .sum("emissions_tonnes")
        .reset_index()
        .assign(aggregation_type="total_ex_lulucf")
    )

    df_agg = pd.concat([df_total, df_total_ex_lulucf])
    # gases_included = ', '.join(df['gas'].unique())

    # finish this
    emissionstotalco2e_validated = [
        EmissionsTotalCO2e(
            id=f"{row.actor_id}:{row.year}:{row.assessment_report}:{row.aggregation_type}",
            actor_id=row.actor_id,
            year=row.year,
            emissions=row.emissions_tonnes,
            aggregation_type=AggregationType(row.aggregation_type),
            units="CO2 tonnes / yr",
            gases_included=gases_included,
            assessment_report=AssessmentReport(row.assessment_report),
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_agg.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalCO2e.__tablename__,
        data=emissionstotalco2e_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
