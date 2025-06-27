import csv
from pathlib import Path
import subprocess

import pandas as pd
import psycopg
from psycopg import Cursor
from rich import print
from sqlmodel import SQLModel
import typer

import models

# this the default database url if one is not specified
# this is just running postgres on localhost
DEFAULT_URL = "postgresql://postgres:postgres@127.0.0.1:5432/ghgtracker"

app = typer.Typer()


def clean_record(record):
    """conerts empty strings to None"""
    for key, value in record.items():
        if value in ("", "null"):
            record[key] = None
    return record


def insert_record(curs: Cursor, table: str, pkey: str, record: dict):
    """insert a single record into the the database"""

    columns = list(record.keys())
    values = [record[col] for col in columns]

    placeholders = ", ".join(["%s"] * len(values))
    column_names = ", ".join([f'"{col}"' for col in columns])

    # on a primary key conflict we are forcing the update
    # may want to think about this choice ...
    query = f"""
    INSERT INTO "{table}" ({column_names})
    VALUES ({placeholders})
    ON CONFLICT ("{pkey}") DO UPDATE SET updated_at = NOW();
    """

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


def bulk_insert(curs: Cursor, table: str, csv_path: str):
    """Insert CSV file using psycopg v3 COPY FROM STDIN"""
    # Get column names from CSV
    columns = pd.read_csv(csv_path, nrows=0).columns.tolist()
    column_names = ", ".join([f'"{col}"' for col in columns])

    with open(csv_path, "r", encoding="utf-8") as f:
        curs.copy(
            f'COPY "{table}" ({column_names}) FROM STDIN WITH CSV HEADER',
            f,
        )


def bulk_insert_from_csv(csv_path, table, database_url):
    """sequentially insert into the database from a csv file"""
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as curs:
            bulk_insert(curs, table, csv_path)
            conn.commit()


def psql_copy(csv_path: Path, table: str, database_url: str):
    """Use `psql` command: `\copy table_name from csv_file with csv header`
    THIS DOES NOT WORK FOR SOME TABLES
    """

    abs_path = csv_path.resolve()

    # Get column names from CSV
    columns = pd.read_csv(csv_path, nrows=0).columns.tolist()
    column_names = ", ".join([f'"{col}"' for col in columns])

    command = [
        "psql",
        database_url,
        "-c",
        f"\\copy {table} ({column_names})  FROM '{abs_path}' WITH CSV HEADER",
    ]

    print(f"[cyan]Running: {' '.join(command)}")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[red]Error importing {table} from {abs_path}:\n{e}")


@app.command()
def sequential(source: str, url: str = DEFAULT_URL):
    # all tables in dependcy order
    sorted_tables = [table.name for table in SQLModel.metadata.sorted_tables]

    # list files in datasource in depdency order
    # this ensure I can run the CLI from anywhere
    # and it will still resolve the path correctly
    path = Path(__file__).resolve().parent.parent / "data" / source / "processed"

    print(f"[green]importing {source} from {path}")

    csv_files = [p.stem for p in path.glob("*.csv")]
    tables_to_import = [table for table in sorted_tables if table in csv_files]

    for table in tables_to_import:
        print(f"[green]    populating the {table} table...")
        csv_file = path / f"{table}.csv"
        insert_from_csv(csv_file, table, url, pkey="id")

    print(f"[green]\nSuccessfully imported {source} into the database !!\n")


@app.command()
def bulk(source: str, url: str = DEFAULT_URL):
    """this does not work, runs sucessfully, but nothing imports
    considering just using the psql command:
        psql $DATABASE_URL -c "\copy table_name FROM 'path/to/file.csv' WITH CSV HEADER"
    """
    # all tables in dependcy order
    sorted_tables = [table.name for table in SQLModel.metadata.sorted_tables]

    # list files in datasource in depdency order
    # this ensure I can run the CLI from anywhere
    # and it will still resolve the path correctly
    path = Path(__file__).resolve().parent.parent / "data" / source / "processed"

    print(f"[green]importing {source} from {path}")

    csv_files = [p.stem for p in path.glob("*.csv")]
    tables_to_import = [table for table in sorted_tables if table in csv_files]

    for table in tables_to_import:
        print(f"[green]    populating the {table} table...")
        csv_file = path / f"{table}.csv"
        # psql_copy(csv_file, table, url) # <--uses psql \copy, does not work
        bulk_insert_from_csv(csv_file, table, url)  # <--uses psycopg, but does not work

    print(f"[green]\nSuccessfully imported {source} into the database !!\n")


if __name__ == "__main__":
    app()
