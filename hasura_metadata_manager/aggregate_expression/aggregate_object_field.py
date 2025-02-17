import logging
from typing import Optional, Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from . import AggregateExpression

logger = logging.getLogger(__name__)


class AggregateObjectField(Base):
    """Represents an aggregatable field in an aggregate expression"""
    __tablename__ = "aggregate_object_field"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    aggregate_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    field_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    aggregate_expression_type: Mapped[str] = mapped_column(String(255))

    @property
    def name(self):
        return self.field_name

    # Relationship back to parent
    aggregate_expression: Mapped["AggregateExpression"] = TemporalRelationship(
        "AggregateExpression",
        uselist=False,
        primaryjoin="""and_(
            foreign(AggregateObjectField.aggregate_name) == AggregateExpression.name,
            foreign(AggregateObjectField.subgraph_name) == AggregateExpression.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["AggregateObjectField"], json_data: Dict[str, Any],
                  aggregate: "AggregateExpression", session: Session) -> "AggregateObjectField":
        logger.debug(f"Creating AggregateObjectField for aggregate {aggregate.name}")

        field = cls(
            aggregate_name=aggregate.name,
            subgraph_name=aggregate.subgraph_name,
            field_name=json_data["fieldName"],
            description=json_data.get("description"),
            aggregate_expression_type=json_data["aggregateExpression"]
        )
        logger.debug(f"Created field with name={field.field_name}, type={field.aggregate_expression_type}")

        session.add(field)
        session.flush()
        return field

    def to_json(self) -> Dict[str, Any]:
        """Convert the field to its original JSON structure"""
        logger.debug(f"Starting to_json serialization for aggregate object field: {self.name}")
        result = {
            "fieldName": self.field_name,
            "description": self.description,
            "aggregateExpression": self.aggregate_expression_type
        }
        if self.description:
            result["description"] = self.description
        logger.debug(f"Completed to_json serialization for {self.name}")
        return result
