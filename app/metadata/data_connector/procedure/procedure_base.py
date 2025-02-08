from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class Procedure(Base):
    """Represents a stored procedure."""
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(String(1023))
    result_type_name: Mapped[Optional[str]] = mapped_column(String(255))
    result_type_subgraph_name: Mapped[Optional[str]] = mapped_column(String(255))
    result_type_connector_name: Mapped[Optional[str]] = mapped_column(String(255))
