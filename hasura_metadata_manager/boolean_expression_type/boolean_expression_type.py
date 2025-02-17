import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Mapped, Session

from .boolean_expression_type_base import \
    BooleanExpressionType as BaseBooleanExpressionType
from .boolean_expression_type_operator import BooleanExpressionTypeOperator
from .comparable_field import ComparableField
from .comparable_relationship import ComparableRelationship
from .data_connector_operator_mapping import DataConnectorOperatorMapping
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..subgraph.subgraph_base import Subgraph

logger = logging.getLogger(__name__)


class BooleanExpressionType(BaseBooleanExpressionType):
    """
    BooleanExpressionType represents a type that can be used in boolean expressions.
    It can be either a scalar type with comparison operators or an object type with comparable fields.
    """
    __tablename__ = "boolean_expression_type"

    # Relationship to Subgraph
    subgraph: Mapped[Subgraph] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(Subgraph.name == foreign(BooleanExpressionType.subgraph_name))"
    )

    # Relationship to operators
    operators: Mapped[List["BooleanExpressionTypeOperator"]] = TemporalRelationship(
        "BooleanExpressionTypeOperator",
        uselist=True,
        viewonly=True,
        primaryjoin="and_(BooleanExpressionTypeOperator.subgraph_name == foreign(BooleanExpressionType.subgraph_name))",
        info={'skip_constraint': True}
    )

    # Direct comparable fields (where this is the parent)
    comparable_fields: Mapped[List["ComparableField"]] = TemporalRelationship(
        "ComparableField",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(BooleanExpressionType.subgraph_name) == ComparableField.subgraph_name,
            foreign(BooleanExpressionType.name) == ComparableField.boolean_expression_type_name,
        ) """,
        info={'skip_constraint': True}
    )

    # Relationship to ComparableRelationships
    comparable_relationships: Mapped[List["ComparableRelationship"]] = TemporalRelationship(
        "ComparableRelationship",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(BooleanExpressionType.subgraph_name) == ComparableRelationship.subgraph_name,
            foreign(BooleanExpressionType.name) == ComparableRelationship.boolean_expression_type_name,
        )""",
        info={'skip_constraint': True}
    )

    # Relationship to DataConnectorOperatorMappings
    data_connector_mappings: Mapped[List["DataConnectorOperatorMapping"]] = TemporalRelationship(
        "DataConnectorOperatorMapping",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(BooleanExpressionType.subgraph_name) == DataConnectorOperatorMapping.subgraph_name,
            foreign(BooleanExpressionType.name) == DataConnectorOperatorMapping.boolean_expression_type_name,
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls, json_data: Dict[str, Any], subgraph: "Subgraph",
                  session: Session) -> Optional["BooleanExpressionType"]:
        """
        Create a BooleanExpressionType instance from JSON data.

        Args:
            json_data: Dictionary containing the boolean expression type definition
            subgraph: The subgraph this type belongs to
            session: SQLAlchemy session

        Returns:
            Optional[BooleanExpressionType]: The created boolean expression type, or None if invalid
        """
        logger.debug(f"Creating BooleanExpressionType from JSON for subgraph {subgraph.name}")

        if json_data.get("kind") != "BooleanExpressionType":
            msg = f"Expected BooleanExpressionType, got {json_data.get('kind')}"
            logger.error(msg)
            raise ValueError(msg)

        def_data = json_data.get("definition", {})
        operand_data = def_data.get("operand", {})

        bool_expr_type = cls(
            name=def_data["name"],
            subgraph_name=subgraph.name,
            graphql_type_name=def_data.get("graphql", {}).get("typeName"),
            is_null_enabled=def_data.get("isNull", {}).get("enable", False),
            logical_ops_enabled=def_data.get("logicalOperators", {}).get("enable", False),
            scalar_type=operand_data.get("scalar", {}).get("type")
        )
        logger.debug(f"Created BooleanExpressionType: {bool_expr_type.name} "
                     f"with scalar_type={bool_expr_type.scalar_type}")

        session.add(bool_expr_type)
        session.flush()

        # Handle scalar operand
        if "scalar" in operand_data:
            scalar_data = operand_data["scalar"]
            logger.debug(f"Processing scalar operand for {bool_expr_type.name}")

            # Process comparison operators
            if "comparisonOperators" in scalar_data:
                logger.debug(f"Processing {len(scalar_data['comparisonOperators'])} comparison operators")
                for op_data in scalar_data["comparisonOperators"]:
                    BooleanExpressionTypeOperator.from_json(op_data, bool_expr_type, session)

            # Process data connector mappings
            if "dataConnectorOperatorMapping" in scalar_data:
                logger.debug(f"Processing {len(scalar_data['dataConnectorOperatorMapping'])} connector mappings")
                for mapping_data in scalar_data["dataConnectorOperatorMapping"]:
                    DataConnectorOperatorMapping.from_json(mapping_data, bool_expr_type, session)

        # Handle object operand
        if "object" in operand_data:
            object_data = operand_data["object"]
            logger.debug(f"Processing object operand for {bool_expr_type.name}")

            # Process comparable fields
            if "comparableFields" in object_data:
                logger.debug(f"Processing {len(object_data['comparableFields'])} comparable fields")
                for field_data in object_data["comparableFields"]:
                    ComparableField.from_json(field_data, bool_expr_type, session)

            # Process comparable relationships
            if "comparableRelationships" in object_data:
                logger.debug(f"Processing {len(object_data['comparableRelationships'])} comparable relationships")
                for rel_data in object_data["comparableRelationships"]:
                    ComparableRelationship.from_json(rel_data, bool_expr_type, session)

        logger.debug(f"Completed BooleanExpressionType creation: {bool_expr_type.name}")
        return bool_expr_type

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the boolean expression type to a JSON-compatible dictionary.
        """
        result = {
            "kind": "BooleanExpressionType",
            "version": "v1",
            "definition": {
                "name": self.name,
                "graphql": {
                    "typeName": self.graphql_type_name
                },
                "isNull": {
                    "enable": self.is_null_enabled
                },
                "logicalOperators": {
                    "enable": self.logical_ops_enabled
                },
                "operand": {}
            }
        }

        if self.scalar_type:
            result["definition"]["operand"]["scalar"] = {
                "type": self.scalar_type,
                "comparisonOperators": [op.to_json() for op in self.operators],
                "dataConnectorOperatorMapping": [
                    mapping.to_json() for mapping in self.data_connector_mappings
                ]
            }

        if self.comparable_fields:
            result["definition"]["operand"]["object"] = {
                "type": self.name.replace("BoolExp", ""),
                "comparableFields": [field.to_json() for field in self.comparable_fields],
                "comparableRelationships": [rel.to_json() for rel in self.comparable_relationships]
            }

        return result

    def __repr__(self) -> str:
        """String representation of the BooleanExpressionType"""
        return f"<BooleanExpressionType(name={self.name}, subgraph={self.subgraph_name})>"
