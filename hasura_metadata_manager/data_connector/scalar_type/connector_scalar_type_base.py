from typing import TYPE_CHECKING, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base

if TYPE_CHECKING:
    pass


class ConnectorScalarType(Base):
    """
    Base class for ConnectorScalarType that defines the schema and attributes.
    This is a specialized form of ScalarType that is associated with a DataConnector.
    """
    __abstract__ = True

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Reference to representation
    representation_name: Mapped[Optional[str]] = mapped_column(String(255))
