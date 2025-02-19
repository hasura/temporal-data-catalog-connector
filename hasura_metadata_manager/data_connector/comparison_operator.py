from typing import Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .type_definition import TypeDefinition
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..boolean_expression_type.boolean_expression_type_base import BooleanExpressionType
    from .scalar_type.connector_scalar_type import ConnectorScalarType

logger = __import__("logging").getLogger(__name__)


class ComparisonOperator(Base):
    """
    Represents a comparison operator in a boolean expression type.
    Stores type information as strings to be later associated with physical objects.
    Handles both simple operators (type only) and custom operators (with argument type).
    """
    __tablename__ = "comparison_operator"

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    boolean_expression_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Type information stored as strings
    operator_type: Mapped[str] = mapped_column(String(255))  # e.g., "equal", "custom", "in"
    connector_name: Mapped[str] = mapped_column(String(255))

    # Foreign keys for argument type
    argument_type_connector_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    argument_type_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Foreign keys for scalar type
    scalar_type_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scalar_type_connector_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scalar_type_subgraph_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    data_connector = TemporalRelationship(
        "DataConnector",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ComparisonOperator.connector_name) == DataConnector.name, 
            foreign(ComparisonOperator.subgraph_name) == DataConnector.subgraph_name
        )"""
    )

    boolean_expression_type = TemporalRelationship(
        "BooleanExpressionType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ComparisonOperator.subgraph_name) == BooleanExpressionType.subgraph_name,
            foreign(ComparisonOperator.boolean_expression_type_name) == BooleanExpressionType.name
        )"""
    )

    argument_type = TemporalRelationship(
        "TypeDefinition",
        viewonly=True,
        primaryjoin="""and_(
            foreign(ComparisonOperator.argument_type_connector_name) == TypeDefinition.connector_name,
            foreign(ComparisonOperator.argument_type_name) == TypeDefinition.name,
            foreign(ComparisonOperator.subgraph_name) == TypeDefinition.subgraph_name
        )"""
    )

    scalar_type = TemporalRelationship(
        "ConnectorScalarType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ComparisonOperator.scalar_type_name) == ConnectorScalarType.name, 
            foreign(ComparisonOperator.scalar_type_connector_name) == ConnectorScalarType.connector_name, 
            foreign(ComparisonOperator.scalar_type_subgraph_name) == ConnectorScalarType.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls, name: str, json_data: Dict[str, Any], parent: "BooleanExpressionType",
                  connector_name: str, session: Session,
                  scalar_type: Optional["ConnectorScalarType"] = None) -> "ComparisonOperator":
        """
        Create a ComparisonOperator from JSON data, handling both simple and custom operators.

        Args:
            name: operator name
            json_data: Dictionary containing operator information
            parent: Parent BooleanExpressionType instance
            connector_name: Associated DataConnector instance
            session: SQLAlchemy session
            scalar_type: Optional ConnectorScalarType instance this operator belongs to

        Returns:
            ComparisonOperator instance
        """
        logger.debug(f"Creating ComparisonOperator for parent {parent.name}")

        operator_type = json_data.get("type")

        # Initialize with common fields
        operator_data = {
            "name": name,
            "subgraph_name": parent.subgraph_name,
            "boolean_expression_type_name": parent.name,
            "connector_name": connector_name,
            "operator_type": operator_type
        }

        # Set scalar type if provided
        if scalar_type:
            operator_data.update({
                "scalar_type_name": scalar_type.name,
                "scalar_type_connector_name": scalar_type.connector_name,
                "scalar_type_subgraph_name": scalar_type.subgraph_name
            })

        # Handle argument type if present
        if argument_type_info := json_data.get("argument_type"):
            # Create or get the TypeDefinition instance
            argument_type = TypeDefinition.from_json(
                type_info={"type": argument_type_info},
                connector_name=connector_name,
                subgraph_name=parent.subgraph_name,
                session=session
            )

            operator_data.update({
                "argument_type_connector_name": argument_type.connector_name,
                "argument_type_name": argument_type.name
            })

        comparison_op = cls(**operator_data)
        session.add(comparison_op)
        session.flush()
        return comparison_op

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the operator to a JSON-compatible dictionary.
        Handles both simple and custom operators.
        """
        result = {
            "type": self.operator_type
        }

        # Add argument type information only for custom operators
        if self.operator_type == "custom" and self.argument_type:
            result["argument_type"] = self.argument_type.to_json()

        return result

    def __repr__(self) -> str:
        """String representation of the ComparisonOperator"""
        base_repr = f"<ComparisonOperator(name={self.name}, type={self.operator_type}"
        if self.argument_type:
            base_repr += f", argument_type={self.argument_type.name}"
        if self.scalar_type:
            base_repr += f", scalar_type={self.scalar_type.name}"
        return base_repr + ")>"
