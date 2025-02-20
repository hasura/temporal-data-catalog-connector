from typing import Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, Session

from ...base import Base
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .. import DataConnector


class MutationCapability(Base):
    __tablename__ = "mutation_capability"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    explain_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    transactional_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    data_connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        primaryjoin="""and_(
            foreign(MutationCapability.connector_name) == DataConnector.name,
            foreign(MutationCapability.subgraph_name) == DataConnector.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["MutationCapability"], json_data: Dict[str, Any],
                  connector: "DataConnector", session: Session) -> "MutationCapability":
        """Create MutationCapabilities from JSON data"""
        # Get mutation data
        capabilities = cls(
            connector_name=connector.name,
            subgraph_name=connector.subgraph_name,
            explain_enabled=isinstance(json_data.get("explain"), dict),  # Check for presence rather than value
            transactional_enabled=isinstance(json_data.get("transactional"), dict)  # Same for transactional
        )
        session.add(capabilities)
        session.flush()

        return capabilities

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the MutationCapability to a JSON-compatible dictionary
        that matches the metadata.json structure.
        """
        mutation_details = {}

        # Add explain capability if enabled
        if self.explain_enabled:
            mutation_details['explain'] = {}

        # Add transactional capability if enabled
        if self.transactional_enabled:
            mutation_details['transactional'] = {}

        return mutation_details
