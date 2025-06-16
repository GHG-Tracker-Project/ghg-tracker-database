import csv
from pathlib import Path
from typing import List
from typing import Dict

import pandas as pd


def write_csv(
    output_dir: str = None,
    name: str = None,
    data: List[Dict] | Dict = None,
    mode: str = "w",
    extension: str = "csv",
) -> None:
    """converts dictionary to CSV"""
    if isinstance(data, dict):
        data = [data]

    file = Path(output_dir).resolve() / f"{name}.{extension}"
    with file.open(mode=mode) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def display_excel_sheets(fl):
    return pd.ExcelFile(fl).sheet_names
