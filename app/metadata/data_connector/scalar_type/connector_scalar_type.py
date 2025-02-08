import logging
from typing import Dict, List, Any, TYPE_CHECKING, cast

from sqlalchemy import and_
from sqlalchemy.orm import Mapped, Session

from ..representation.representation import Representation
from ..scalar_type.aggregate_function import AggregateFunction
from ..scalar_type.connector_scalar_type_base import \
    ConnectorScalarType as BaseConnectorScalarType
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .. import DataConnector
    from ..comparison_operator import ComparisonOperator
    from ... import BooleanExpressionType

logger = logging.getLogger(__name__)


class ConnectorScalarType(BaseConnectorScalarType):
    __tablename__ = "connector_scalar_type"

    # Add the relationship to comparison operators
    comparison_operators: Mapped[List["ComparisonOperator"]] = TemporalRelationship(
        "ComparisonOperator",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ConnectorScalarType.name) == ComparisonOperator.scalar_type_name,
            foreign(ConnectorScalarType.connector_name) == ComparisonOperator.scalar_type_connector_name,
            foreign(ConnectorScalarType.subgraph_name) == ComparisonOperator.scalar_type_subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    representation: Mapped["Representation"] = TemporalRelationship(
        "Representation",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ConnectorScalarType.connector_name) == Representation.connector_name,
            foreign(ConnectorScalarType.representation_name) == Representation.name,
            foreign(ConnectorScalarType.subgraph_name) == Representation.subgraph_name
        )"""
    )

    aggregate_functions: Mapped[List["AggregateFunction"]] = TemporalRelationship(
        "AggregateFunction",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ConnectorScalarType.name) == AggregateFunction.scalar_type_name, 
            foreign(ConnectorScalarType.subgraph_name) == AggregateFunction.return_type_subgraph_name, 
            foreign(ConnectorScalarType.connector_name) == AggregateFunction.return_type_connector_name
        )""",
        info={'skip_constraint': True}
    )

    data_connector = TemporalRelationship(
        "DataConnector",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ConnectorScalarType.connector_name) == DataConnector.name, 
            foreign(ConnectorScalarType.subgraph_name) == DataConnector.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls, name: str, type_data: Dict[str, Any],
                  connector: "DataConnector", session: Session) -> "ConnectorScalarType":
        from ..representation import Representation

        # Create representation first if it exists
        representation = None
        if "representation" in type_data:
            representation = Representation.from_json(
                type_data["representation"],
                subgraph_name=connector.subgraph_name,
                connector_name=connector.name,
                name=f"{name}_representation",  # Create a unique name for the representation
                session=session
            )
            session.add(representation)
            session.flush()

        # Create scalar type
        scalar_type = cls(
            name=name,
            connector_name=connector.name,
            subgraph_name=connector.subgraph_name,
            representation_name=representation.name if representation else None
        )
        session.add(scalar_type)
        session.flush()

        # Find appropriate boolean expression types
        from ...boolean_expression_type.boolean_expression_type import BooleanExpressionType, \
            DataConnectorOperatorMapping

        # Look for boolean expression types with matching data connector mappings
        boolean_expression_types = cast(List[BooleanExpressionType], session.query(BooleanExpressionType).join(
            BooleanExpressionType.data_connector_mappings
        ).filter(and_(
            BooleanExpressionType.subgraph_name == connector.subgraph_name,
            DataConnectorOperatorMapping.data_connector_scalar_type == name,
            DataConnectorOperatorMapping.data_connector_name == connector.name
        )).all())

        # Process comparison operators
        from ..comparison_operator import ComparisonOperator
        comparison_operators = type_data.get("comparison_operators", {})
        for op_name, op_details in comparison_operators.items():
            if not boolean_expression_types:
                raise ValueError(f"No boolean expression type found for scalar type {name}")

            # Use the first matching boolean expression type
            boolean_expression_type = boolean_expression_types[0]

            ComparisonOperator.from_json(
                op_name,
                op_details,
                boolean_expression_type,
                connector,
                session,
                scalar_type
            )

        # Process aggregate functions
        from ..scalar_type.aggregate_function import AggregateFunction
        for function_name, function_type in type_data.get("aggregate_functions", {}).items():
            AggregateFunction.from_json(scalar_type.name, function_name, function_type, connector, session)

        return scalar_type

    def to_json(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "representation": self.representation.to_json() if self.representation else None,
            "comparisonOperators": {
                op.name: op.to_json() for op in self.comparison_operators
            },
            "aggregateFunctions": {
                func.function_name: func.to_json() for func in self.aggregate_functions
            }
        }
