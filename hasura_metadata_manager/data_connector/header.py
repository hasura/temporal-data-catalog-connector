from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..data_connector import DataConnector


class Header(Base):
    """Model for storing headers for a data connector."""
    __tablename__ = "data_connector_header"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String(1024))
    is_response_header: Mapped[bool] = mapped_column(Boolean, default=False)

    data_connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        primaryjoin="""and_(
            foreign(Header.connector_name) == DataConnector.name, 
            foreign(Header.subgraph_name) == DataConnector.subgraph_name, 
            foreign(Header.is_response_header) == False
        )"""
    )
