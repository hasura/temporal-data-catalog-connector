from typing import Dict, Any, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .boolean_expression_type import BooleanExpressionType


class BooleanExpressionTypeOperator(Base):
    """
    Represents a comparison operator that can be used with a boolean expression type.
    Examples include _eq, _gt, _lt etc. with their GraphQL argument types.
    """
    __tablename__ = "boolean_expression_type_operator"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    boolean_expression_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Full GraphQL type including modifiers (e.g., "Bytea!", "[Bytea!]!")
    argument_type: Mapped[str] = mapped_column(String(255))

    # Base scalar type name without modifiers (e.g., "Bytea")
    scalar_type_name: Mapped[str] = mapped_column(String(255))

    # Relationship back to parent BooleanExpressionType
    boolean_expression_type: Mapped["BooleanExpressionType"] = TemporalRelationship(
        "BooleanExpressionType",
        uselist=False,
        primaryjoin="""and_(
            foreign(BooleanExpressionTypeOperator.subgraph_name) == BooleanExpressionType.subgraph_name, 
            foreign(BooleanExpressionTypeOperator.boolean_expression_type_name) == BooleanExpressionType.name
            )""",
    )

    @staticmethod
    def parse_graphql_type(graphql_type: str) -> str:
        """
        Parse a GraphQL type string to get the base scalar type name.

        Args:
            graphql_type: GraphQL type string (e.g., "Bytea!", "[Bytea!]!")

        Returns:
            str: The base scalar type name without modifiers
        """
        base_type = graphql_type

        # Remove list brackets if present
        if base_type.startswith('[') and base_type.endswith(']'):
            base_type = base_type[1:-1]

        # Remove non-null modifiers
        return base_type.replace('!', '')

    def to_json(self) -> Dict[str, Any]:
        """Convert the operator to a JSON-compatible dictionary"""
        return {
            "name": self.name,
            "argumentType": self.argument_type
        }

    @classmethod
    def from_json(cls, operator_data: Dict[str, Any],
                  boolean_expression_type: "BooleanExpressionType",
                  session: Session) -> "BooleanExpressionTypeOperator":
        """Create a BooleanExpressionTypeOperator from JSON data"""
        graphql_type = operator_data["argumentType"]
        base_type = cls.parse_graphql_type(graphql_type)

        operator = cls(
            name=operator_data["name"],
            argument_type=graphql_type,
            scalar_type_name=base_type,
            subgraph_name=boolean_expression_type.subgraph_name,
            boolean_expression_type_name=boolean_expression_type.name
        )
        session.add(operator)
        session.flush()
        return operator

    def __repr__(self) -> str:
        """String representation"""
        return (f"<BooleanExpressionTypeOperator("
                f"name={self.name}, "
                f"argument_type={self.argument_type}, "
                f"scalar_type={self.scalar_type_name})>")
