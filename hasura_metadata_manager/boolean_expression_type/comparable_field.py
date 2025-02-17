from typing import Dict, Any, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .boolean_expression_type_base import BooleanExpressionType
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

logger = __import__("logging").getLogger(__name__)


class ComparableField(Base):
    __tablename__ = "comparable_field"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    parent_name: Mapped[str] = mapped_column(String(255), primary_key=True)  # References parent BooleanExpressionType
    field_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    boolean_expression_type_name: Mapped[str] = mapped_column(String(255))  # References another BooleanExpressionType

    # Relationship to parent BooleanExpressionType
    parent: Mapped["BooleanExpressionType"] = TemporalRelationship(
        "BooleanExpressionType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ComparableField.parent_name) == BooleanExpressionType.name, 
            foreign(ComparableField.subgraph_name) == BooleanExpressionType.subgraph_name
        )"""
    )

    # Relationship to referenced BooleanExpressionType
    boolean_expression_type: Mapped["BooleanExpressionType"] = TemporalRelationship(
        "BooleanExpressionType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ComparableField.boolean_expression_type_name) == BooleanExpressionType.name,
            foreign(ComparableField.subgraph_name) == BooleanExpressionType.subgraph_name
        )"""
    )

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary"""
        return {
            "fieldName": self.field_name,
            "booleanExpressionType": self.boolean_expression_type_name
        }

    @classmethod
    def from_json(cls, json_data: Dict[str, Any], parent: "BooleanExpressionType",
                  session: Session) -> Optional["ComparableField"]:
        logger.debug(f"Creating ComparableField for parent {parent.name}")
        if not json_data:
            logger.debug("No JSON data provided for ComparableField")
            return None

        comparable_field = cls(
            field_name=json_data.get("fieldName"),
            subgraph_name=parent.subgraph_name,
            parent_name=parent.name,
            boolean_expression_type_name=json_data.get("booleanExpressionType")
        )
        logger.debug(f"Created ComparableField: {comparable_field.field_name} "
                     f"with bool_expr_type={comparable_field.boolean_expression_type_name}")

        session.add(comparable_field)
        session.flush()
        return comparable_field

    def __repr__(self):
        return f"<ComparableField(name={self.field_name}, boolean_expression_type={self.boolean_expression_type_name})>"
