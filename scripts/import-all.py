#
# imports all data into the database
# python -m scripts.import-all
#
import csv
from pathlib import Path

import psycopg
from psycopg import Cursor
from sqlmodel import SQLModel

import models


def clean_record(record):
    """conerts empty strings to None"""
    for key, value in record.items():
        if value in ("", "null"):
            record[key] = None
    return record


def insert_record(curs: Cursor, table: str, pkey: str, record: dict):
    """insert a single record into the the database"""
    # now = datetime.now()

    # record['created'] = now
    # record['last_updated'] = now

    columns = list(record.keys())
    values = [record[col] for col in columns]

    placeholders = ", ".join(["%s"] * len(values))
    column_names = ", ".join([f'"{col}"' for col in columns])

    query = f"""
    INSERT INTO "{table}" ({column_names})
    VALUES ({placeholders})
    """
    # ON CONFLICT ("{pkey}") DO UPDATE SET
    # last_updated = EXCLUDED.last_updated

    curs.execute(query, values)


def insert_from_csv(csv_path, table, database_url, pkey="id"):
    """sequentially insert into the database from a csv file"""
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as curs:
            with open(csv_path, newline="") as csvfile:
                reader = csv.DictReader(csvfile)
                for record in reader:
                    clean_record(record)
                    insert_record(curs, table, pkey, record)

            conn.commit()


# bad practice to hard code in database url
database_url = "postgresql://postgres:postgres@127.0.0.1:5432/ghgtracker"

# all tables in dependcy order
sorted_tables = [table.name for table in SQLModel.metadata.sorted_tables]

# loop over all files in manifest
with open("./data/manifest.txt", "r") as manifest:
    for source in manifest.readlines():
        source = source.strip()
        print(source)

        # list files in datasource in depdency order
        # source = "iso-3166-1"
        path = Path(f"./data/{source}/processed")
        csv_files = [p.stem for p in path.glob("*.csv")]
        tables_to_import = [table for table in sorted_tables if table in csv_files]

        for table in tables_to_import:
            print(table)
            csv_file = path / f"{table}.csv"
            insert_from_csv(csv_file, table, database_url, pkey="id")
