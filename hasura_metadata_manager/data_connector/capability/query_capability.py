from typing import Type, Dict, Any

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..data_connector_base import DataConnector
from ...base import Base
from ...mixins.temporal.temporal_relationship import TemporalRelationship


class QueryCapability(Base):
    __tablename__ = "query_capability"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    aggregates_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    exists_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    explain_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    nested_fields_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    variables_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    nested_collections_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    filter_by_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    order_by_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    data_connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        primaryjoin="""and_(
            foreign(QueryCapability.connector_name)==DataConnector.name, 
            foreign(QueryCapability.subgraph_name)==DataConnector.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["QueryCapability"], json_data: Dict[str, Any],
                  connector: "DataConnector", session: Session) -> "QueryCapability":
        """Create QueryCapability from JSON data"""
        query_data = json_data
        capability = cls(
            connector_name=connector.name,
            subgraph_name=connector.subgraph_name,
            # Check for key presence rather than truthiness
            aggregates_enabled=bool(query_data.get("aggregates")),
            exists_enabled=isinstance(query_data.get("explain"), dict),
            explain_enabled=isinstance(query_data.get("explain"), dict),
            nested_fields_enabled=isinstance(query_data.get("nested_fields"), dict),
            variables_enabled=isinstance(query_data.get("variables"), dict),
            # Check for nested key presence
            nested_collections_enabled="nested_collections" in query_data.get("exists", {}),
            filter_by_enabled="filter_by" in query_data.get("nested_fields", {}),
            order_by_enabled="order_by" in query_data.get("nested_fields", {})
        )
        session.add(capability)
        session.flush()

        return capability

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the QueryCapability to a JSON-compatible dictionary
        that matches the metadata.json structure.
        """
        query_details = {}

        # Add aggregates capability
        if self.aggregates_enabled:
            query_details['aggregates'] = {}

        # Add exists capability
        if self.exists_enabled:
            query_details['exists'] = {}
            if self.nested_collections_enabled:
                query_details['exists']['nested_collections'] = {}

        # Add explain capability
        if self.explain_enabled:
            query_details['explain'] = {}

        # Add nested fields capability
        if self.nested_fields_enabled:
            query_details['nested_fields'] = {}
            if self.filter_by_enabled:
                query_details['nested_fields']['filter_by'] = {}
            if self.order_by_enabled:
                query_details['nested_fields']['order_by'] = {}

        # Add variables capability
        if self.variables_enabled:
            query_details['variables'] = {}

        return query_details
