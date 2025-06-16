from datetime import datetime
from pathlib import Path

import pandas as pd

from models import DataSource, TargetType, Targets
from utils import write_csv


def main():
    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "net-zero-tracker"
    publisher = "Net Zero Tracker"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name=datasource_name,
        publisher=publisher,
        published_date=datetime.strptime("2025-06-04", "%Y-%m-%d"),
        version="2025-06-04",
        url="https://zerotracker.net/",
    )

    # load data
    # Note: Path(__file__).resolve().parent.parent same as "../"
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # input dataset
    fl = data_dir / "raw" / "current_snapshot_2025-06-04_12-07-45.xlsx"

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

    df_actors = pd.read_csv(fl_actors)[
        ["#country_code_alpha2", "country_code_alpha3"]
    ].rename(
        columns={"#country_code_alpha2": "actor_id", "country_code_alpha3": "iso3"}
    )

    write_csv(
        output_dir=output_dir,
        name=datasource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # some notes on different target types in Net Zero Tracker
    # ['Emissions reduction target', <-- definitely track these
    # 'Absolute emissions target',   <--- this one can be recast into an Emission reduction target
    # 'Reduction v. BAU'             <--- this one can be recast into an Emission reduction target
    # 'Emissions intensity target',  <-- no sure we want to track these
    # 'Net zero', 'Net negative',  'GHG neutral(ity)', 'Carbon neutral(ity)',  <--- these are all similar
    # 'Zero emissions', 'Zero carbon', 'Carbon negative', <-- these are all similar
    # 'Climate positive', 'Climate neutral', <-- these are all similar
    # 'Other',  'No target',  nan] <-- not very useful

    columns_end = [
        "Name",
        "Country",
        "Entity_type",  # ['Country', 'Region', 'City', 'Company']
        "End_target",  # target type
        "End_target_percentage_reduction",
        "End_target_baseline_year",
        "End_target_year",
        "Status_of_end_target",
        "Date_of_last_status_update",
        "End_target_text",
        "End_target_source_url",
    ]

    columns_interim = [
        "Name",
        "Country",  # this is the iso3 code
        "Entity_type",  # this is actor_type
        "Interim_target",
        "Interim_target_year",
        "Interim_target_percentage_reduction",
        "Interim_target_baseline_year",
        "Interim_target_text",
        "End_target_source_url",
    ]

    # ------------------------------------------
    # process raw data
    # ------------------------------------------
    # !!todo: validation for url check if start with http:// or https://
    # end targets
    df_end = (
        pd.read_excel(fl, sheet_name="Current Snapshot", header=1)
        .loc[:, columns_end]
        .query(
            "End_target=='Emissions reduction target' and End_target_percentage_reduction.notnull()"
        )
        .query("End_target_baseline_year.notnull()")
        .query("Entity_type=='Country'")
        .rename(
            columns={
                "End_target": "target_type",
                "End_target_year": "target_year",
                "End_target_percentage_reduction": "percent_reduction",
                "End_target_baseline_year": "baseline_year",
                "End_target_text": "target_text",
                "End_target_source_url": "url",
            }
        )
    )

    # interim targets
    df_interim = (
        pd.read_excel(fl, sheet_name="Current Snapshot", header=1)
        .loc[:, columns_interim]
        .query(
            "Interim_target=='Emissions reduction target' and Interim_target_percentage_reduction.notnull()"
        )
        .query("Interim_target_baseline_year.notnull()")
        .query("Entity_type=='Country'")
        .rename(
            columns={
                "Interim_target": "target_type",
                "Interim_target_year": "target_year",
                "Interim_target_percentage_reduction": "percent_reduction",
                "Interim_target_baseline_year": "baseline_year",
                "Interim_target_text": "target_text",
                "End_target_source_url": "url",
            }
        )
    )

    df_tmp = pd.concat([df_end, df_interim])

    # merge on actors to get actor_id
    df = (
        pd.merge(df_tmp, df_actors, left_on="Country", right_on="iso3")
        .loc[
            :,
            [
                "actor_id",
                "target_type",
                "percent_reduction",
                "baseline_year",
                "target_year",
                "url",
            ],
        ]
        .fillna({"url": ""})
        .astype(
            {
                "actor_id": str,
                "target_type": str,
                "percent_reduction": float,
                "baseline_year": int,
                "target_year": int,
                "url": str,
            }
        )
        .sort_values(by=["actor_id", "target_year"])
        .drop_duplicates()
    )

    # ------------------------------------------
    # target table
    # ------------------------------------------
    target_type = TargetType.absolute_reduction

    # model dump returns as dictionary
    targets_validated = [
        Targets(
            id=f"{row.actor_id}:{target_type.value.replace(' ', '-')}:{row.target_year}",
            actor_id=row.actor_id,
            target_type=target_type,
            target_value=row.percent_reduction,
            baseline_year=row.baseline_year,
            target_year=row.target_year,
            url=row.url,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Targets.__tablename__,
        data=targets_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
