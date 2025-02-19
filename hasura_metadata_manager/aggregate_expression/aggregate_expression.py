import logging
from typing import List, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Mapped

from .aggregate_expression_base import AggregateExpression as BaseAggregateExpression
from .aggregate_object_field import AggregateObjectField
from .aggregate_scalar_function import AggregateScalarFunction
from .data_connector_function_mapping import DataConnectorFunctionMapping
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..relationship import Relationship

logger = logging.getLogger(__name__)


class AggregateExpression(BaseAggregateExpression):
    """
    Represents an aggregate expression used for analyzing and processing data within a subgraph.
    The class provides functionality for converting aggregate definitions to and from JSON structure and facilitates the relationship mapping for various components like object fields, scalar functions, and data connectors.

    Attributes:
     - `object_fields`: List of fields associated with the aggregate object definition, representing individual objects that can be aggregated.
     - `aggregate_scalar_functions`: List of scalar functions associated with the aggregate expression, representing operations applicable to scalar data types.
     - `data_connector_function_mappings`: List of mappings for data connectors and their respective function definitions, which define how the aggregate scalar functions map to specific data connector functions.
     - `target_relationships`: List of relationships where the aggregate expression acts as the target type.

    Methods:
     - `to_json`: Converts the aggregate expression and its associated data into a JSON representation that follows the original structure defined for such aggregates.
        - Logs the overall serialization process.
        - Includes information such as description, count configuration, GraphQL hasura_metadata_manager, operands (objects and scalars), and their associated mappings.
     - `from_json`: Class method that reconstructs an aggregate expression from its JSON representation.
        - Verifies the correctness and type of the input JSON structure.
        - Maps the operand data (object and scalar types) to appropriate attributes.
        - Deserializes related objects (e.g., fields, scalar functions, and mappings) and associates them with the aggregate expression.
        - Handles database session persistence.
        - Logs the entire deserialization process, including validation checks and processing of related components.
    """
    __tablename__ = "aggregate_expression"

    # Relationships
    object_fields: Mapped[List["AggregateObjectField"]] = TemporalRelationship(
        "AggregateObjectField",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(AggregateExpression.name) == AggregateObjectField.aggregate_name,
            foreign(AggregateExpression.subgraph_name) == AggregateObjectField.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    aggregate_scalar_functions: Mapped[List["AggregateScalarFunction"]] = TemporalRelationship(
        "AggregateScalarFunction",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(AggregateExpression.name) == AggregateScalarFunction.aggregate_name,
            foreign(AggregateExpression.subgraph_name) == AggregateScalarFunction.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    # In AggregateExpression class
    data_connector_function_mappings: Mapped[List["DataConnectorFunctionMapping"]] = TemporalRelationship(
        "DataConnectorFunctionMapping",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(AggregateExpression.name) == DataConnectorFunctionMapping.aggregate_name, 
            foreign(AggregateExpression.subgraph_name) == DataConnectorFunctionMapping.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    target_relationships: Mapped[List["Relationship"]] = TemporalRelationship(
        "Relationship",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(AggregateExpression.name) == Relationship.target_type_name, 
            foreign(AggregateExpression.subgraph_name) == Relationship.target_subgraph_name
            )""",
        info={'skip_constraint': True}
    )

    def to_json(self) -> Dict[str, Any]:
        """Convert the aggregate expression to its original JSON structure"""
        logger.debug(f"Starting to_json serialization for aggregate expression: {self.name}")

        definition = {
            "name": self.name,
            "description": self.description,
            "count": {
                "enable": self.count_enabled,
                "description": self.count_description,
                "returnType": self.count_return_type,
            } if self.count_enabled or self.count_description else None,
            "countDistinct": {
                "enable": self.count_distinct_enabled,
                "description": self.count_distinct_description,
                "returnType": self.count_distinct_return_type,
            } if self.count_distinct_enabled is not None or self.count_distinct_description else None,
            "graphql": {
                "selectTypeName": self.graphql_select_type_name,
                "deprecated": self.graphql_deprecated
            },
            "operand": {}
        }

        # Add object fields if present
        if self.object_fields:
            logger.debug(f"Processing {len(self.object_fields)} object fields for {self.name}")
            definition["operand"]["object"] = {
                "aggregatableFields": [
                    field.to_json() for field in self.object_fields
                ],
                "aggregatedType": self.operand_object_aggregate_type
            }

        connector_mappings = {}
        if self.operand_scalar_type:
            logger.debug(f"Processing scalar type {self.operand_scalar_type} for {self.name}")

            # Group mappings by data connector
            for mapping in self.data_connector_function_mappings:
                if mapping.data_connector_name not in connector_mappings:
                    connector_mappings[mapping.data_connector_name] = {
                        "dataConnectorName": mapping.data_connector_name,
                        "dataConnectorScalarType": mapping.data_connector_scalar_type,
                        "functionMapping": {}
                    }
                if mapping.function_name and mapping.function_name.strip():
                    connector_mappings[mapping.data_connector_name]["functionMapping"][
                        mapping.function_name
                    ] = mapping.to_json()

            agg_type = self.operand_scalar_type or self.operand_object_aggregate_type
            logger.debug(f"Created {len(connector_mappings)} data connector mappings for {self.name}")

            # Create the list
            data_connector_aggregation_function_mapping = list(connector_mappings.values())

            definition["operand"]["scalar"] = {
                "aggregatedType": agg_type,
                "aggregationFunctions": [func.to_json() for func in self.aggregate_scalar_functions],
                "dataConnectorAggregationFunctionMapping": data_connector_aggregation_function_mapping
            }

        logger.debug(f"Completed to_json serialization for {self.name}")
        return {
            "kind": "AggregateExpression",
            "version": "v1",
            "definition": definition
        }

    @classmethod
    def from_json(cls, json_data, subgraph, session):
        logger.debug(f"Starting from_json deserialization for {json_data.get('definition', {}).get('name')}")

        if json_data.get("kind") != "AggregateExpression":
            error_msg = f"Expected AggregateExpression, got {json_data.get('kind')}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        def_data = json_data.get("definition", {})
        operand_data = def_data.get("operand", {})

        operand_object_aggregate_type = None
        operand_scalar_type = None

        if "object" in operand_data:
            logger.debug("Processing object operand data")
            object_data = operand_data["object"]
            operand_object_aggregate_type = object_data.get("aggregatedType")

        if "scalar" in operand_data:
            logger.debug("Processing scalar operand data")
            scalar_data = operand_data["scalar"]
            operand_scalar_type = scalar_data.get("aggregatedType")

        aggregate = cls(
            name=def_data["name"],
            subgraph_name=subgraph.name,
            operand_object_aggregate_type=operand_object_aggregate_type,
            operand_scalar_type=operand_scalar_type,
            description=def_data.get("description"),
            count_enabled=def_data.get("count", {}).get("enable", False),
            count_description=def_data.get("count", {}).get("description"),
            count_return_type=def_data.get("count", {}).get("returnType"),
            count_distinct_enabled=(def_data.get("countDistinct", {}) or {}).get("enable"),
            count_distinct_description=(def_data.get("countDistinct", {}) or {}).get("description"),
            count_distinct_return_type=(def_data.get("countDistinct", {}) or {}).get("returnType"),
            graphql_select_type_name=(def_data.get("graphql", {}) or {}).get("selectTypeName"),
            graphql_deprecated=(def_data.get("graphql", {}) or {}).get("deprecated", False)
        )
        session.add(aggregate)
        session.flush()

        if "object" in operand_data:
            fields_data = operand_data["object"].get("aggregatableFields", [])
            logger.debug(f"Creating {len(fields_data)} object fields")
            for field_data in fields_data:
                AggregateObjectField.from_json(field_data, aggregate, session)
                if fields_data.index(field_data) % 50 == 0:  # Added
                    session.flush()  # Added

        if "scalar" in operand_data:
            scalar_data = operand_data["scalar"]
            logger.debug(f"Creating scalar functions for type {operand_scalar_type}")

            # Create scalar functions
            funcs_data = scalar_data.get("aggregationFunctions", [])
            logger.debug(f"Processing {len(funcs_data)} scalar functions")
            for func_data in funcs_data:
                AggregateScalarFunction.from_json(
                    {
                        "name": func_data["name"],
                        "returnType": func_data["returnType"],
                        "description": func_data.get("description")
                    },
                    operand_scalar_type,
                    aggregate,
                    session
                )
                if funcs_data.index(func_data) % 50 == 0:  # Added
                    session.flush()  # Added

            # Process data connector mappings
            if "dataConnectorAggregationFunctionMapping" in scalar_data:
                mappings_data = scalar_data["dataConnectorAggregationFunctionMapping"]
                logger.debug(f"Processing {len(mappings_data)} data connector mappings")
                for mapping_data in mappings_data:
                    mappings = DataConnectorFunctionMapping.from_json(
                        mapping_data,
                        aggregate,
                        session
                    )
                    session.add_all(mappings)
                    if mappings_data.index(mapping_data) % 10 == 0:  # Added
                        session.flush()  # Added
                        session.expire_all()  # Added

            session.flush()
            session.expire_all()  # Added

        session.flush()
        logger.debug(f"Completed from_json deserialization for {aggregate.name}")
        return aggregate
