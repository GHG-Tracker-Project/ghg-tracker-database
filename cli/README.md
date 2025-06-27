# Importer CLI

This contains a [typer](https://typer.tiangolo.com/)-based CLI to import datasets into the database.
This is a work in progress.

syntax:

```sh
importer seqential SOURCE
```

for example, if you want to import `iso-3166-1` country names, then you run:

```sh
importer seqential iso-3166-1
```

## Notes
- May want to think about choice of what happens `ON CONFLICT`
- All data imports sequentially. Add an option to import an entire dataset at once using the `COPY` command in postgres.
- Have an option scrub data database. Useful when we update datasources. Have this be a different CLI `importer` is just for ingesting data into the database and `scrubber` is to remove data from the database. 
- consider a `db-stats` CLI that lists datasources in each table?
