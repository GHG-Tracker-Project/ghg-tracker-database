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
    """Insert CSV file using psycopg v3 COPY FROM STDIN
    for very large files, you want to chunk the file.
    replace copy.write(f.read()) with :
    while data := f.read(8192):
        copy.write(data)
    """
    # Get column names from CSV
    columns = pd.read_csv(csv_path, nrows=0).columns.tolist()
    column_names = ", ".join([f'"{col}"' for col in columns])

    query = f'COPY "{table}" ({column_names}) FROM STDIN WITH CSV HEADER'

    with open(csv_path, "r", encoding="utf-8") as f:
        with curs.copy(query) as copy:
            copy.write(f.read())


def bulk_insert_with_staging(
    curs: Cursor, table: str, csv_path: str, primary_key: str = "id"
):
    """
    Load CSV into a temporary staging table first,
    then insert into target table skipping duplicates on primary key.
    """
    # Get column names from CSV
    columns = pd.read_csv(csv_path, nrows=0).columns.tolist()
    column_names = ", ".join([f'"{col}"' for col in columns])

    staging_table = f"staging_{table}"

    # Create temporary staging table
    curs.execute(
        f"""
        CREATE TEMP TABLE {staging_table} (LIKE "{table}" INCLUDING ALL)
    """
    )

    # Copy CSV into staging table
    copy_query = f"COPY {staging_table} ({column_names}) FROM STDIN WITH CSV HEADER"

    with open(csv_path, "r", encoding="utf-8") as f:
        with curs.copy(copy_query) as copy:
            copy.write(f.read())

    # Insert into the actual table and skip duplicates
    insert_query = f"""
        INSERT INTO "{table}" ({column_names})
        SELECT {column_names}
        FROM {staging_table}
        ON CONFLICT ("{primary_key}") DO NOTHING
        """
    curs.execute(insert_query)


def bulk_upsert_with_staging(curs: Cursor, table: str, csv_path: str):
    """
    Automatically determines primary key from database,
    then loads csv into staging and upserts into target table.
    In other words, this will update rows that change
    and insert new rows
    """

    # Get columns from CSV
    columns = pd.read_csv(csv_path, nrows=0).columns.tolist()
    column_names = ", ".join([f'"{col}"' for col in columns])

    staging_table = f"staging_{table}"

    # Look up primary key columns automatically
    curs.execute(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass AND i.indisprimary
    """,
        (table,),
    )
    pk_columns = [row[0] for row in curs.fetchall()]
    if not pk_columns:
        raise ValueError(f"Table {table} has no primary key defined.")
    conflict_clause = ", ".join([f'"{col}"' for col in pk_columns])

    # Build the DO UPDATE SET clause (skip pk columns)
    update_columns = [col for col in columns if col not in pk_columns]
    if update_columns:
        update_set_clause = ", ".join(
            [f'"{col}" = EXCLUDED."{col}"' for col in update_columns]
        )
        on_conflict_action = f"DO UPDATE SET {update_set_clause}"
    else:
        # If no updatable columns (only PK), fallback to DO NOTHING
        on_conflict_action = "DO NOTHING"

    # Create temp staging table
    curs.execute(f'CREATE TEMP TABLE {staging_table} (LIKE "{table}" INCLUDING ALL)')

    # Copy CSV into staging table
    copy_query = f"COPY {staging_table} ({column_names}) FROM STDIN WITH CSV HEADER"
    with open(csv_path, "r", encoding="utf-8") as f:
        with curs.copy(copy_query) as copy:
            copy.write(f.read())

    # Insert with ON CONFLICT DO UPDATE
    insert_query = f"""
        INSERT INTO "{table}" ({column_names})
        SELECT {column_names}
        FROM {staging_table}
        ON CONFLICT ({conflict_clause})
        {on_conflict_action}
    """
    curs.execute(insert_query)


def bulk_insert_from_csv(csv_path, table, database_url):
    """sequentially insert into the database from a csv file"""
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as curs:
            # bulk_insert_with_staging(curs, table, csv_path)
            bulk_upsert_with_staging(curs, table, csv_path)
            conn.commit()


@app.command()
def sequential(source: str, url: str = DEFAULT_URL):
    """Imports each record seqentially.
    Use this when there are recursive foreign keys in the table"""
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
    """Imports all records at once.
    Use this when there are no recursive foreign keys in the table
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
        bulk_insert_from_csv(csv_file, table, url)

    print(f"[green]\nSuccessfully imported {source} into the database !!\n")


if __name__ == "__main__":
    app()
