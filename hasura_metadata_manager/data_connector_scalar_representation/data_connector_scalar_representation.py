from typing import Dict, Any

from sqlalchemy.orm import Mapped, Session

from .data_connector_scalar_representation_base import \
    DataConnectorScalarRepresentation as BaseDataConnectorScalarRepresentation
from ..data_connector.scalar_type import ConnectorScalarType
from ..data_connector.schema.scalar_type.scalar_type import ScalarType
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..subgraph.subgraph_base import Subgraph


class DataConnectorScalarRepresentation(BaseDataConnectorScalarRepresentation):
    __tablename__ = "data_connector_scalar_representation"

    # Relationship to ScalarType
    scalar_type: Mapped["ScalarType"] = TemporalRelationship(
        "ScalarType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnectorScalarRepresentation.scalar_type_name) == ScalarType.name, 
            foreign(DataConnectorScalarRepresentation.subgraph_name) == ScalarType.subgraph_name
        )"""
    )
    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        viewonly=True,
        primaryjoin="Subgraph.name == foreign(DataConnectorScalarRepresentation.subgraph_name)"
    )
    connector_scalar_type: Mapped["ConnectorScalarType"] = TemporalRelationship(
        "ConnectorScalarType",
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnectorScalarRepresentation.data_connector_scalar_type) == ConnectorScalarType.name, 
            foreign(DataConnectorScalarRepresentation.data_connector_name) == ConnectorScalarType.connector_name, 
            foreign(DataConnectorScalarRepresentation.subgraph_name) == ConnectorScalarType.subgraph_name
        )""",
    )

    @classmethod
    def from_json(cls, json_data: Dict[str, Any], subgraph: Subgraph, session: Session):
        """
        Create a DataConnectorScalarRepresentation from JSON data.
        """
        definition = json_data.get("definition", {})

        scalar_rep = cls(
            data_connector_name=definition.get("dataConnectorName", ""),
            subgraph_name=subgraph.name,
            data_connector_scalar_type=definition.get("dataConnectorScalarType", ""),
            scalar_type_name=definition.get("representation", ""),
            graphql_comparison_expression_type_name=definition.get("graphql", {}).get("comparisonExpressionTypeName")
        )

        session.add(scalar_rep)
        session.flush()
        return scalar_rep

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the DataConnectorScalarRepresentation to JSON format.
        """
        definition = {
            "dataConnectorName": self.data_connector_name,
            "dataConnectorScalarType": self.data_connector_scalar_type,
            "representation": self.scalar_type_name
        }

        # Add optional GraphQL comparison expression type name if it exists
        if self.graphql_comparison_expression_type_name:
            definition["graphql"] = {
                "comparisonExpressionTypeName": self.graphql_comparison_expression_type_name
            }

        return {
            "definition": definition,
            "kind": "DataConnectorScalarRepresentation",
            "version": "v1"
        }
