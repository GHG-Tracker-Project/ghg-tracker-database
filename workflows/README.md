# Workflows

This directory contains different workflows. For now, we are only using this to populate the database.
In the future, we may consider using this system to update raw datasources.

Within each directory you can run the workflow with:

```sh
dvc repro
```

You can visualize the dag with 

```sh
dvc dag
```

and if you want to force the pipeline to run and not use cahce you can use:

```sh
dvc repro --force
```

# Alternative solutions
Not sure I want to keep this solution. Another options include:
- [Airflow](https://airflow.apache.org/)
- [snakemake](https://snakemake.readthedocs.io/en/stable/)
- [prefect](https://www.prefect.io/?utm_source=Google&utm_medium=CPC&utm_campaign=Brand&gad_source=1&gad_campaignid=22149507517)
- [luigi](https://luigi.readthedocs.io/en/stable/)

I am leaning toward snakemake or keeping dvc because I like the simplicity of defining workflows with yaml. Since dvc is intended for machine learning, maybe it is worth learning more about snakemake?