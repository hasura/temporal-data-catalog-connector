from enum import Enum
from typing import Optional

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class RelationshipType(Enum):
    ARRAY = 'Array'
    OBJECT = 'Object'


class Relationship(Base):
    """Base class containing all shared relationship attributes."""
    __abstract__ = True

    # Primary key columns from base class
    subgraph_name: Mapped[str] = mapped_column(primary_key=True)
    source_type_name: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, primary_key=True)

    # Other columns from base class
    target_type_name: Mapped[str] = mapped_column(String)
    target_subgraph_name: Mapped[str] = mapped_column(String)
    relationship_type: Mapped[str] = mapped_column(String)
    graphql_field_name: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    deprecated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Additional fields specific to this implementation
    is_aggregate: Mapped[bool] = mapped_column(Boolean, default=False)
    aggregate_expression: Mapped[Optional[str]] = mapped_column(String)
