from typing import Optional, Dict, Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .boolean_expression_type_base import BooleanExpressionType
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

logger = __import__("logging").getLogger(__name__)


class ComparableRelationship(Base):
    __tablename__ = "comparable_relationship"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    parent_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    relationship_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    boolean_expression_type_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    aggregate_boolean_expression_type_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    parent: Mapped["BooleanExpressionType"] = TemporalRelationship(
        "BooleanExpressionType",
        uselist=False,
        primaryjoin="""and_(
            foreign(ComparableRelationship.parent_name) == BooleanExpressionType.name,
            foreign(ComparableRelationship.subgraph_name) == BooleanExpressionType.subgraph_name
        )"""
    )

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary"""
        return {
            "relationshipName": self.relationship_name,
            "booleanExpressionType": self.boolean_expression_type_name,
            "aggregateBooleanExpressionType": self.aggregate_boolean_expression_type_name
        }

    @classmethod
    def from_json(cls, json_data: Dict[str, Any], parent: "BooleanExpressionType",
                  session: Session) -> Optional["ComparableRelationship"]:
        """Create a ComparableRelationship from JSON data."""
        logger.debug(f"Creating ComparableRelationship for parent {parent.name}")
        if not json_data:
            logger.debug("No JSON data provided for ComparableRelationship")
            return None

        relationship = cls(
            relationship_name=json_data.get("relationshipName"),
            subgraph_name=parent.subgraph_name,
            parent_name=parent.name,
            boolean_expression_type_name=json_data.get("booleanExpressionType"),
            aggregate_boolean_expression_type_name=json_data.get("aggregateBooleanExpressionType")
        )
        logger.debug(f"Created ComparableRelationship: {relationship.relationship_name} "
                     f"with bool_expr_type={relationship.boolean_expression_type_name}, "
                     f"agg_type={relationship.aggregate_boolean_expression_type_name}")

        session.add(relationship)
        session.flush()
        return relationship
