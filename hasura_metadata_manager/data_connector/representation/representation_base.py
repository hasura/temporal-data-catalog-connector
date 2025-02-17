from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class Representation(Base):
    """Base class for scalar type representations"""
    __abstract__ = True

    # Natural key columns - matching the pattern from TypeDefinition
    subgraph_name: Mapped[Optional[str]] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Using String instead of Enum for dynamic type support
    type: Mapped[str] = mapped_column(String(255))
