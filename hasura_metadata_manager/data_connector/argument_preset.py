from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..data_connector import DataConnector


class ArgumentPreset(Base):
    """Model for storing argument presets for a data connector."""
    __tablename__ = "data_connector_argument_preset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255))
    subgraph_name: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(String(1024))
    argument_type: Mapped[str] = mapped_column(String(50))

    data_connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        primaryjoin="""and_(
            foreign(ArgumentPreset.connector_name) == DataConnector.name, 
            foreign(ArgumentPreset.subgraph_name) == DataConnector.subgraph_name
        )"""
    )
