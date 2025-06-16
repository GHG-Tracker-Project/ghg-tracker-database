#
# GHGTracker Schema
# these tables are used to setup the database
# and serve as way to validate any data imported into the database
#
# author: Luke Gloege
# Created: 2025-04-28
#

from enum import Enum
from sqlmodel import SQLModel, Column, Field, TIMESTAMP, text, FetchedValue
from typing import Optional
from datetime import datetime


# track external data sources for actor, emissions, targets, and contexual data
class DataSource(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    publisher: Optional[str]
    published_date: Optional[datetime]
    version: Optional[str]
    url: Optional[str]
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


# ensure actor type is correct
class ActorType(str, Enum):
    planet = "planet"
    country = "country"
    territory = "territory"
    adm1 = "adm1"
    adm2 = "adm2"
    city = "city"


# table to track actors (country, subnational, city)
class Actor(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    is_part_of: Optional[str] = Field(default=None, foreign_key="actor.id")
    type: ActorType
    sovereign_code: Optional[str] = Field(default=None, foreign_key="actor.id")
    datasource_id: Optional[str] = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


# ============================================================
#
# Emissions contexual data
# these tables help provide additional details on the emissions
# gas, sector, conversion factors, ...
#
# ============================================================


class Gas(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class GWP(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    gwp100: float
    gas_id: str = Field(foreign_key="gas.id")
    datasource_id: Optional[str] = Field(default=None, foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class Sector(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    parend_id: Optional[str] = Field(default=None, foreign_key="actor.id")
    level: str
    description: Optional[str]
    datasource_id: Optional[str] = Field(default=None, foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


# ============================================================
#
# Emissions and Targets tables
#
# ============================================================


class EmissionsTotalExLULUCF(SQLModel, table=True):
    id: str = Field(primary_key=True)
    actor_id: str = Field(foreign_key="actor.id")
    year: int
    emissions: float
    units: str
    datasource_id: str = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class Emissions(SQLModel, table=True):
    id: str = Field(primary_key=True)
    actor_id: str = Field(foreign_key="actor.id")
    year: int
    sector: str = Field(foreign_key="sector.id")
    emissions: float
    units: str
    datasource_id: str = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class TargetType(str, Enum):
    """this will grow, but for now we will only absolute emission reductions"""

    absolute_reduction = "absolute_reduction"
    target_reduction = "target_reduction"


class Targets(SQLModel, table=True):
    id: str = Field(primary_key=True)
    actor_id: str = Field(foreign_key="actor.id")
    target_type: TargetType
    target_value: float
    baseline_year: int
    target_year: int
    url: Optional[str]
    datasource_id: str = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


# ============================================================
#
# Contextual data
# these tables provide additional information on the actors
# and were intially intended for use with the Kaya identity
#
# ============================================================


class GDP(SQLModel, table=True):
    id: str = Field(primary_key=True)
    year: int
    actor_id: str = Field(foreign_key="actor.id")
    gdp: float
    datasource_id: str = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class Population(SQLModel, table=True):
    id: str = Field(primary_key=True)
    year: int
    actor_id: str = Field(foreign_key="actor.id")
    population: int
    datasource_id: str = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class EnergyConsumption(SQLModel, table=True):
    id: str = Field(primary_key=True)
    year: int
    actor_id: str = Field(foreign_key="actor.id")
    consumption: float
    datasource_id: str = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        # default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )
