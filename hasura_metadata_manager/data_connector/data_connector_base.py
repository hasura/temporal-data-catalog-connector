from enum import Enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ArgumentType(Enum):
    SCALAR = 'scalar'
    PREDICATE = 'predicate'
    COLLECTION = 'collection'


class DataConnector(Base):
    """Base class for DataConnector that defines the schema and attributes."""
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    read_url: Mapped[str] = mapped_column(String(1024))
    write_url: Mapped[str] = mapped_column(String(1024))
    schema_version: Mapped[str] = mapped_column(String(255))
