from typing import Type, Dict, Any

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..data_connector_base import DataConnector
from ...base import Base
from ...mixins.temporal.temporal_relationship import TemporalRelationship


class RelationshipCapability(Base):
    __tablename__ = "relationship_capability"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    order_by_aggregate_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    relation_comparisons_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    data_connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        primaryjoin="""and_(
            foreign(RelationshipCapability.connector_name)==DataConnector.name, 
            foreign(RelationshipCapability.subgraph_name)==DataConnector.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["RelationshipCapability"], json_data: Dict[str, Any],
                  connector: "DataConnector", session: Session) -> "RelationshipCapability":
        """Create RelationshipCapabilities from JSON data"""
        rel_data = json_data
        capabilities = cls(
            connector_name=connector.name,
            subgraph_name=connector.subgraph_name,
            order_by_aggregate_enabled="order_by_aggregate" in rel_data,
            relation_comparisons_enabled="relation_comparisons" in rel_data
        )
        session.add(capabilities)
        session.flush()

        return capabilities

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the RelationshipCapability to a JSON-compatible dictionary
        that matches the metadata.json structure.
        """
        relationship_details = {}

        # Add order by aggregate capability
        if self.order_by_aggregate_enabled:
            relationship_details['order_by_aggregate'] = {}

        # Add relation comparisons capability
        if self.relation_comparisons_enabled:
            relationship_details['relation_comparisons'] = {}

        return relationship_details
