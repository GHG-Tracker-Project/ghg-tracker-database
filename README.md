# GHG Tracker Project

The GHG Tracker Project provides comprehensive data on greenhouse gas (GHG) emissions and climate targets, focusing on both national and subnational actors (e.g., states, provinces, and cities). The project harmonizes emissions data and target information into a common framework. Its goal is to create a comprehensive, open-source database that serves as a reliable resource for researchers, policymakers, and stakeholders.

GHG Tracker collects and organizes data on emissions by sector and gas wherever possible. It also integrates national and subnational emission reduction pledges. In addition, the database includes contextual information such as population, GDP, and energy consumption, providing a more complete picture of the drivers behind emissions changes through frameworks like the Kaya identity.

GHG Tracker Database is written entirely in Python to facilitate easier collaboration, maintainability, and integration with the broader data science ecosystem. The first phase of the project is building out the database. The next phase will be a high-level API that makes it easy to query the database. 

## Python Envionrment setup
We use [uv](https://docs.astral.sh/uv/) as our package manager for this project. If you want a crash course in uv, I suggest [Corey Schafer's tutorial](https://www.youtube.com/watch?v=AMdG7IjgSPM). The steps below will outline how to get started:

1. Install uv. See the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) to find instructions on how to install uv for your operating system. If you are on MacOS, and use the [homebrew](https://brew.sh/) package manager, then you can use the following command:
```sh
brew install uv
``` 
2. Once installed, you can setup your virtual environment with the following command: 
```sh
uv sync
```

That's all there is to it becauase all the information to setup the environment is in the `uv.lock` and `pyporoject.toml` files. 

> [!NOTE]  
> We may have to add additional packages in the future. In that case, use `uv add PackageName` to update `pyproject.toml` and `uv.lock`. Then open a merge request to update the `.toml` and `.lock` files. 


## Database Setup

We use Docker and Docker Compose to setup the database. Here are the steps to get start developing the database locally. 

1. Make sure you [Docker](https://docs.docker.com/get-started/get-docker/) installed on your machine.
2. Make sure you are in the same directory as this `README.md` file. 
3. Copy the command below to rename the envionrment variable file.
This creates environment variables so you can access the database in the coming steps
```sh
mv ./.env-example ./.env
```
4. Start the database in a container and expose it on localhost port 5432 with the following command.
```sh
docker-compose up -d
```

How you have an empty [Postgres](https://www.postgresql.org/) database server running in a Docker container. Any data you add to the database will persist in a docker volume. What this means is when you stop the container or even remove the container, the database will persist. 

> [!NOTE]  
> In lieu of using Docker, you could install a Postgres server on your computer. Steps to do this will be added in future.

### Query the database
There is no data in here ... yet. But when there is, one tool you can use is `psql` to send SQL queries to the database. Here the connection string:

```sh
psql -h localhost -p 5432 -U postgres -W -d ghgtracker
```

Alternatively, you could use a scripting language such as Python with the `psycopg` package to query the database. Dealer's choice.

### Stopping the database

Use the folling command
```sh
docker-compose down
```


## Database migrations

We use [alembic](https://alembic.sqlalchemy.org/en/latest/) for migrations and have it setup to autogenerate. What this means is all you have to do is change the schema in `models/models.py`. Then to create the migration file you run the following:

```sh
alembic revision --autogenerate -m "put message here" --rev-id $(date +"%Y%m%d%H%M%S")
```

this will create a new migration file with your given message in `./migrations/versions/`, it will use the timestamp as the revision `id`

Use the following command to apply the change:

```sh
alembic upgrade head
```

> [!NOTE]  
> since we are still in development phase, let's stick with a single migration file for the time being.
