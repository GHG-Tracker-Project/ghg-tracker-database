from datetime import datetime
from pathlib import Path

import pandas as pd

from models import DataSource, GDP
from utils import write_csv


def main():

    # datasource names
    datasource_name = "world-bank"
    publisher = "World Bank Group"

    # load data
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------
    # get all country codes
    # ------------------------------------------
    # get actors information
    # !note: we are grabbing from the raw dataset
    # may be doing this a lot
    # let's make a function that gets iso2 and iso3 names
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
    # datasource table
    # ------------------------------------------
    datasource = DataSource(
        id=f"{publisher.replace(" ", "_")}:{datasource_name}",
        name="GDP Constant 2015 US$ (NY.GDP.MKTP.KD)",
        publisher=publisher,
        published_date=datetime.strptime("2024-01-01", "%Y-%m-%d"),
        version="2024",
        url="https://data.worldbank.org/indicator/NY.GDP.MKTP.KD",
    )

    write_csv(
        output_dir=output_dir,
        name=datasource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # population table
    # ------------------------------------------
    fl = data_dir / "raw" / "API_NY.GDP.MKTP.KD_DS2_en_csv_v2_81108.csv"

    # read the raw data
    # doing this to make it easier to get value_vars (i.e. the years)
    df_tmp = pd.read_csv(fl, header=2, keep_default_na=False)
    df_tmp = df_tmp.loc[:, ~df_tmp.columns.str.startswith("Unnamed:")]

    id_vars = ["Country Name", "Country Code", "Indicator Name", "Indicator Code"]
    value_vars = list(set(df_tmp.columns) - set(id_vars))

    df = (
        df_tmp.melt(
            id_vars=id_vars, value_vars=value_vars, var_name="year", value_name="gdp"
        )
        .dropna(subset=["gdp"])
        .query("gdp != ''")  # drop rows where gdp is an empty string
        .merge(df_actors, left_on="Country Code", right_on="iso3")
        .loc[:, ["year", "gdp", "actor_id"]]
        .astype({"actor_id": str, "year": int, "gdp": float})
    )

    validated_data = [
        GDP(
            id=f"{row.actor_id}:{row.year}",
            year=row.year,
            actor_id=row.actor_id,
            gdp=row.gdp,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir, name=GDP.__tablename__, data=validated_data, mode="w"
    )


if __name__ == "__main__":
    main()
