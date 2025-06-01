import csv
from typing import List
from typing import Dict

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

    with open(f"{output_dir}/{name}.{extension}", mode=mode) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
