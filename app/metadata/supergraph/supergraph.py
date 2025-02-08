from datetime import datetime
from typing import List, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from .subgraph_supergraph_map import SubgraphSupergraphMap
from .supergraph_base import Supergraph as BaseSupergraph
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..role.role_base import Role

if TYPE_CHECKING:
    from .. import Subgraph


class Supergraph(BaseSupergraph):
    __tablename__ = "supergraph"

    roles: Mapped[List["Role"]] = TemporalRelationship(
        "Role",
        uselist=True,
        viewonly=True,
        primaryjoin="and_(foreign(Supergraph.name)==Role.supergraph_name)",
        info={'skip_constraint': True}
    )
    subgraph_maps: Mapped[List["SubgraphSupergraphMap"]] = TemporalRelationship(
        "SubgraphSupergraphMap",
        uselist=True,
        viewonly=True,
        primaryjoin="and_(foreign(Supergraph.name)==SubgraphSupergraphMap.supergraph_name)",
        info={'skip_constraint': True})

    @classmethod
    def from_json(cls, json_data: Dict[str, Any], session: Session) -> "Supergraph":
        # Import concrete Subgraph class at runtime
        from ..subgraph import Subgraph  # Deferred import

        supergraph = cls(
            name="default",  # Could be configurable
            version=json_data.get("version", "v1")
        )
        session.add(supergraph)
        session.flush()  # Flush to get the primary key

        # Process subgraphs if present
        if "subgraphs" in json_data:
            for subgraph_data in json_data["subgraphs"]:
                Subgraph.from_json(subgraph_data, supergraph, session)

        return supergraph

    def to_json(self, session: Session) -> Dict[str, Any]:
        """
        Serialize Supergraph to JSON format.

        Args:
            session: SQLAlchemy session

        Returns:
            Dictionary representing the Supergraph in metadata.json format
        """
        # Get subgraphs through mapping table
        subgraphs: List[Subgraph] = [map_entry.subgraph for map_entry in self.subgraph_maps]

        json_dict = {
            'version': self.version,
        }

        if subgraphs:
            json_dict['subgraphs'] = [
                subgraph.to_json(session) for subgraph in subgraphs
            ]

        return json_dict

    def is_updated(self, check_datetime: datetime) -> bool:
        """
        Check if the supergraph has been updated at or after the provided datetime.

        Args:
            check_datetime (datetime): The datetime to check against the supergraph's update time.
                                     Should be a timezone-aware datetime object.

        Returns:
            bool: True if the supergraph was updated at or after check_datetime, False otherwise.

        Raises:
            ValueError: If check_datetime is None or not a datetime object.
        """
        if not isinstance(check_datetime, datetime):
            raise ValueError("check_datetime must be a datetime object")

        # Get the last update time from temporal mixin's t_updated_at
        last_update = self.t_updated_at

        if last_update is None:
            # If there's no update time, use created time
            last_update = self.t_created_at

        # Compare the timestamps
        # Returns True if last_update >= check_datetime
        return last_update >= check_datetime
