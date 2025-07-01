#
# GHGTracker Schema
# these tables are used to setup the database
# and serve as way to validate any data imported into the database
#
# author: Luke Gloege
# Created: 2025-04-28
# Updates:
#   2025-06-23 update emissions breakdown tables

from enum import Enum
from sqlmodel import SQLModel, Column, Field, TIMESTAMP, text, FetchedValue
from typing import Optional
from datetime import datetime

# ============================================================
# Enums
# ============================================================


class ActorType(str, Enum):
    planet = "planet"
    country = "country"
    territory = "territory"
    adm1 = "adm1"
    adm2 = "adm2"
    city = "city"


class AssessmentReport(str, Enum):
    AR1 = "AR1"
    AR2 = "AR2"
    AR3 = "AR3"
    AR4 = "AR4"
    AR5 = "AR5"
    AR6 = "AR6"


class TargetType(str, Enum):
    absolute_reduction = "absolute_reduction"
    target_reduction = "target_reduction"


class AggregationType(str, Enum):
    total = "total"
    total_ex_lulucf = "total_ex_lulucf"


class GasType(str, Enum):
    CO2 = "CO2"
    CH4 = "CH4"
    CH4_fossil = "CH4_fossil"
    CH4_nonfossil = "CH4_nonfossil"
    N2O = "N2O"
    NF3 = "NF3"
    SF6 = "SF6"
    FGASES = "FGASES"
    HFCS = "HFCS"
    PFCS = "PFCS"
    KYOTOGHGS = "KYOTOGHGS"


# ============================================================
# Actor and DataSource
# ============================================================


# track external data sources for actor, emissions, targets, and contexual data
class DataSource(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    publisher: Optional[str]
    published_date: Optional[datetime]
    version: Optional[str]
    url: Optional[str]
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


# table to track actors (country, subnational, city)
class Actor(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    is_part_of: Optional[str] = Field(default=None, foreign_key="actor.id")
    type: ActorType
    sovereign_code: Optional[str] = Field(default=None, foreign_key="actor.id")
    datasource_id: Optional[str] = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
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


class GWP(SQLModel, table=True):
    id: str = Field(primary_key=True)
    gwp: float
    time_horizon: int
    gas: GasType
    assessment_report: AssessmentReport
    datasource_id: Optional[str] = Field(default=None, foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class Sector(SQLModel, table=True):
    id: str = Field(primary_key=True)
    code: str
    parent_code: Optional[str] = Field(default=None, foreign_key="sector.id")
    name: str
    taxonomy: Optional[str]  # this should be a Enum
    description: Optional[str]
    datasource_id: Optional[str] = Field(default=None, foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


# to create a sector dag
# useful if a sector belongs to multiple parent categories
class SectorRelation(SQLModel, table=True):
    parent_id: str = Field(foreign_key="sector.id", primary_key=True)
    child_id: str = Field(foreign_key="sector.id", primary_key=True)


# ============================================================
#
# Emissions and Targets tables
#
# ============================================================


# raw emissions for each gas and sector
class Emissions(SQLModel, table=True):
    id: str = Field(primary_key=True)
    actor_id: str = Field(foreign_key="actor.id")
    gas: GasType
    sector_id: str = Field(foreign_key="sector.id")
    year: int
    emissions: float
    units: str
    datasource_id: Optional[str] = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


# raw emissions in for each gas and sector
# in units of CO2e
# do I even want to include this?
class EmissionsCO2e(SQLModel, table=True):
    id: str = Field(primary_key=True)
    actor_id: str = Field(foreign_key="actor.id")
    sector_id: str = Field(foreign_key="sector.id")
    gas: GasType
    gwp_id: str = Field(foreign_key="gwp.id")
    year: int
    emissions: float
    units: str
    datasource_id: Optional[str] = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class EmissionsTotalSector(SQLModel, table=True):
    id: str = Field(primary_key=True)
    actor_id: str = Field(foreign_key="actor.id")
    sector_id: str = Field(foreign_key="sector.id")
    year: int
    emissions: float
    assessment_report: AssessmentReport
    units: str
    datasource_id: Optional[str] = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


class EmissionsTotalCO2e(SQLModel, table=True):
    id: str = Field(primary_key=True)
    actor_id: str = Field(foreign_key="actor.id")
    year: int
    emissions: float
    aggregation_type: AggregationType
    units: str
    assessment_report: AssessmentReport
    datasource_id: Optional[str] = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )


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
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
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
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
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
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
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
    units: str  # e.g., "TJ", "Mtoe", "GWh"
    fuel_type: str  # e.g., "coal", "solar", "oil" maybe enum?
    energy_source: str  # e.g., "fossil", "renewable" maybe this should be enum?
    datasource_id: str = Field(foreign_key="datasource.id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=FetchedValue(),
        )
    )
