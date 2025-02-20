import logging
from typing import Dict, Type, Any

from sqlalchemy.orm import validates, Session

from .graphql_config_base import GraphQLConfig as BaseGraphQLConfig
from ..subgraph.subgraph_base import Subgraph
from ..type_permission import OperationType

logger = logging.getLogger(__name__)


class GraphQLConfig(BaseGraphQLConfig):
    __tablename__ = "graphql_config"

    @validates('operation_type')
    def validate_operation_type(self, _key, value):
        if value not in [t.value for t in OperationType]:
            raise ValueError(f"Invalid operation_type: {value}")
        return value

    @classmethod
    def from_json(cls: Type["GraphQLConfig"], json_data: Dict[str, Any], subgraph: "Subgraph",
                  session: Session) -> "GraphQLConfig":
        logger.debug(f"Starting GraphQLConfig.from_json with data: {json_data}")

        def_data = json_data.get("definition", {})
        logger.debug(f"Extracted definition data: {def_data}")

        # Extract query config
        query_config = def_data.get("query", {})
        logger.debug(f"Extracted query config: {query_config}")

        aggregate_config = query_config.get("aggregate", {})
        logger.debug(f"Extracted aggregate config: {aggregate_config}")

        filter_input = query_config.get("filterInput", {})
        logger.debug(f"Extracted filter input config: {filter_input}")

        order_by_input = query_config.get("orderByInput", {})
        logger.debug(f"Extracted order by input config: {order_by_input}")

        value = {
            "apollo_federation": def_data.get("apolloFederation"),
            "mutation": def_data.get("mutation"),
            "subscription": def_data.get("subscription"),
            "query": {
                "aggregate": {
                    "countDistinctFieldName": aggregate_config.get("countDistinctFieldName"),
                    "countFieldName": aggregate_config.get("countFieldName"),
                    "filterInputFieldName": aggregate_config.get("filterInputFieldName")
                },
                "argumentsInput": query_config.get("argumentsInput"),
                "filterInput": {
                    "fieldName": filter_input.get("fieldName"),
                    "operatorNames": filter_input.get("operatorNames")
                },
                "limitInput": query_config.get("limitInput"),
                "offsetInput": query_config.get("offsetInput"),
                "orderByInput": {
                    "enumDirectionValues": order_by_input.get("enumDirectionValues"),
                    "enumTypeNames": order_by_input.get("enumTypeNames"),
                    "fieldName": order_by_input.get("fieldName")
                },
                "rootOperationTypeName": query_config.get("rootOperationTypeName")
            }
        }
        logger.debug(f"Constructed value dictionary: {value}")

        operation_type = def_data.get("operationType", OperationType.QUERY.value)
        root_operation_type_name = def_data.get("rootOperationTypeName", "Query")
        apollo_federation_enabled = bool(def_data.get("apolloFederation"))

        logger.debug(f"Creating GraphQLConfig with operation_type: {operation_type}, "
                     f"root_operation_type_name: {root_operation_type_name}, "
                     f"apollo_federation_enabled: {apollo_federation_enabled}")

        config = cls(
            key="default",
            subgraph_name=subgraph.name,
            operation_type=operation_type,
            root_operation_type_name=root_operation_type_name,
            apollo_federation_enabled=apollo_federation_enabled,
            value=value
        )

        logger.debug(f"Created GraphQLConfig instance: {config}")
        session.add(config)
        session.flush()

        logger.debug("Added GraphQLConfig to session")

        return config

    def to_json(self) -> Dict[str, Any]:
        """
        Convert GraphQLConfig instance to JSON format matching metadata.json structure.

        Returns:
            Dict[str, Any]: JSON representation of GraphQL configuration
        """
        logger.debug(f"Current stored value: {self.value}")

        result = {
            "kind": "GraphqlConfig",
            "version": "v1",
            "definition": {
                "apolloFederation": self.value.get("apollo_federation"),
                "mutation": self.value.get("mutation"),
                "query": self.value.get("query"),
                "subscription": self.value.get("subscription")
            }
        }

        logger.debug(f"Generated JSON result: {result}")
        return result
