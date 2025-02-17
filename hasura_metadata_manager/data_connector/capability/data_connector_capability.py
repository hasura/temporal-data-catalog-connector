from typing import Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..capability.mutation_capability import MutationCapability
from ..capability.relationship_capability import RelationshipCapability
from ...base import Base
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .. import DataConnector
    from ..capability.query_capability import QueryCapability


class DataConnectorCapability(Base):
    __tablename__ = "data_connector_capability"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[str] = mapped_column(String(50))
    supports_aggregates: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_nested_fields: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_variables: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_transactions: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_field_filters: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def name(self):
        return self.connector_name

    data_connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        primaryjoin="""and_(
            foreign(DataConnectorCapability.connector_name)==DataConnector.name, 
            foreign(DataConnectorCapability.subgraph_name)==DataConnector.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["DataConnectorCapability"], json_data: Dict[str, Any],
                  connector: "DataConnector", session: Session) -> "DataConnectorCapability":
        """Create a DataConnectorCapabilities from JSON data."""
        capabilities_data = json_data
        cap_details = capabilities_data.get("capabilities", {})

        capabilities = cls(
            connector_name=connector.name,
            subgraph_name=connector.subgraph_name,
            version=capabilities_data.get("version"),
            supports_aggregates="aggregates" in cap_details.get("query", {}),
            supports_nested_fields="nested_fields" in cap_details.get("query", {}),
            supports_variables="variables" in cap_details.get("query", {}),
            supports_transactions="transactional" in cap_details.get("mutation", {}),
            supports_field_filters=bool(cap_details.get("query", {}).get("nested_fields", {}).get("filter_by"))
        )
        session.add(capabilities)
        session.flush()

        if "capabilities" in json_data:
            cap_details = json_data["capabilities"]
            MutationCapability.from_json(cap_details.get("mutation", {}), connector, session)
            # Import QueryCapability here to avoid circular imports
            from ..capability.query_capability import QueryCapability
            QueryCapability.from_json(cap_details.get("query", {}), connector, session)
            RelationshipCapability.from_json(cap_details.get("relationships", {}), connector, session)

        return capabilities

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the DataConnectorCapability to a JSON-compatible dictionary
        that matches the metadata.json structure.
        """
        # Prepare the capabilities details
        capabilities_details = {
            "query": {},
            "mutation": {},
            "relationships": {}
        }

        # Add query capabilities
        if self.supports_aggregates:
            capabilities_details["query"]["aggregates"] = {}
        if self.supports_nested_fields:
            capabilities_details["query"]["nested_fields"] = {
                "filter_by": {}
            }
        if self.supports_variables:
            capabilities_details["query"]["variables"] = {}
        if self.supports_field_filters:
            if "nested_fields" not in capabilities_details["query"]:
                capabilities_details["query"]["nested_fields"] = {}
            capabilities_details["query"]["nested_fields"]["filter_by"] = {}

        # Add mutation capabilities
        if self.supports_transactions:
            capabilities_details["mutation"]["transactional"] = {}

        # Include mutation and relationship capabilities from related models
        if self.data_connector.mutation_capability:
            mutation_details = self.data_connector.mutation_capability.to_json()
            capabilities_details["mutation"].update(mutation_details)

        if self.data_connector.relationship_capability:
            relationship_details = self.data_connector.relationship_capability.to_json()
            capabilities_details["relationships"].update(relationship_details)

        if self.data_connector.query_capability:
            query_details = self.data_connector.query_capability.to_json()
            capabilities_details["query"].update(query_details)

        return {
            "capabilities": capabilities_details,
            "version": self.version
        }
