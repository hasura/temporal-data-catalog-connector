from typing import Optional, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    pass


class EnumValue(Base):
    """Stores possible values for enum representations"""
    __tablename__ = "enum_value"

    subgraph_name: Mapped[Optional[str]] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    rep_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), primary_key=True)

    @property
    def name(self):
        return self.value

    # Relationship back to representation
    representation = TemporalRelationship(
        "Representation",
        primaryjoin="""and_(
            foreign(EnumValue.subgraph_name)==Representation.subgraph_name, 
            foreign(EnumValue.connector_name)==Representation.connector_name, 
            foreign(EnumValue.rep_name)==Representation.name
        )""",
    )

    def to_json(self) -> str:
        """Convert enum value to JSON format"""
        return self.value

    @classmethod
    def from_json(cls, value: str, subgraph_name: Optional[str],
                  connector_name: str, rep_name: str) -> "EnumValue":
        """
        Create an EnumValue instance from JSON data

        Args:
            value: enum value
            subgraph_name: Optional subgraph name
            connector_name: Connector name
            rep_name: Name of the representation this enum value belongs to
        """

        if not value or not isinstance(value, str):
            raise ValueError("Enum value must have a string value")

        return cls(
            subgraph_name=subgraph_name,
            connector_name=connector_name,
            rep_name=rep_name,
            value=value
        )
