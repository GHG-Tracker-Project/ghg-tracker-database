from datetime import datetime
from pathlib import Path

from models import DataSource, GasType, AssessmentReport, GWP
from utils import write_csv


def main():

    # load data
    # Note: Path(__file__).resolve().parent.parent same as "../"
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "gwp"
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    # table 4 page 22
    datasource_ar2 = DataSource(
        id="IPCC:AR2",
        name="Climate Change 1995, the science of climate change",
        publisher="The Intergovernmental Panel on Climate Change",
        published_date=datetime.strptime("1995-01-01", "%Y-%m-%d"),
        url="https://www.ipcc.ch/site/assets/uploads/2018/02/ipcc_sar_wg_I_full_report.pdf",
    )

    # table 3 page 47
    datasource_ar3 = DataSource(
        id="IPCC:AR3",
        name="Climate Change 2001, the scientific basis",
        publisher="The Intergovernmental Panel on Climate Change",
        published_date=datetime.strptime("2001-01-01", "%Y-%m-%d"),
        url="https://www.ipcc.ch/site/assets/uploads/2018/03/WGI_TAR_full_report.pdf",
    )

    # see page 32
    datasource_ar4 = DataSource(
        id="IPCC:AR4",
        name="Climate Change 2007, the physical science basis",
        publisher="The Intergovernmental Panel on Climate Change",
        published_date=datetime.strptime("2007-01-01", "%Y-%m-%d"),
        url="https://www.ipcc.ch/site/assets/uploads/2018/05/ar4_wg1_full_report-1.pdf",
    )

    datasource_ar5 = DataSource(
        id="IPCC:AR5",
        name="Climate Change 2013, the physical science basis",
        publisher="The Intergovernmental Panel on Climate Change",
        published_date=datetime.strptime("2013-01-01", "%Y-%m-%d"),
        url="https://www.ipcc.ch/site/assets/uploads/2018/02/WG1AR5_all_final.pdf",
    )

    datasource_ar6 = DataSource(
        id="IPCC:AR6",
        name="Climate Change 2021, the physical science basis",
        publisher="The Intergovernmental Panel on Climate Change",
        published_date=datetime.strptime("2021-01-01", "%Y-%m-%d"),
        url="https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_FullReport.pdf",
    )

    datasources = dict(
        AR2=datasource_ar2,
        AR3=datasource_ar3,
        AR4=datasource_ar4,
        AR5=datasource_ar5,
        AR6=datasource_ar6,
    )

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=[source.model_dump() for source in datasources.values()],
        mode="w",
    )

    # ------------------------------------------
    # GWP table
    # ------------------------------------------
    raw_gwp100_data = {
        "CH4": {"AR6": 27.9, "AR5": 28, "AR4": 25, "AR3": 23, "AR2": 21},
        "CH4_nonfossil": {
            "AR6": 27,
            "AR5": 28,
        },
        "CH4_fossil": {
            "AR6": 29.8,
            "AR5": 30,
        },
        "N2O": {"AR6": 273, "AR5": 265, "AR4": 298, "AR3": 296, "AR2": 310},
        "NF3": {"AR6": 17400, "AR5": 16100, "AR4": 17200, "AR3": 10800},
        "SF6": {"AR6": 24300, "AR5": 23500, "AR4": 22800, "AR3": 22000, "AR2": 23900},
    }

    # put all GWPS into a list
    gwps = []
    for gas, dic in raw_gwp100_data.items():
        time_horizon = 100
        for assessment_report, gwp in dic.items():
            gwp_tmp = GWP(
                id=f"{gas}:GWP{time_horizon}:{assessment_report}",
                # name = f"GWP-{time_horizon} for {gas} from {assessment_report}", <-- remove this
                gwp=gwp,
                time_horizon=time_horizon,
                gas=GasType(gas),
                assessment_report=AssessmentReport(assessment_report),
                datasource_id=datasources[assessment_report].id,
            )
            gwps.append(gwp_tmp)

    write_csv(
        output_dir=output_dir,
        name=GWP.__tablename__,
        data=[gwp.model_dump() for gwp in gwps],
        mode="w",
    )


if __name__ == "__main__":
    main()
