from datetime import datetime
from typing import Type, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from .compatibility_config_base import CompatibilityConfig as BaseCompatibilityConfig
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..subgraph.subgraph_base import Subgraph


class CompatibilityConfig(BaseCompatibilityConfig):
    """Represents compatibility configuration"""
    __tablename__ = "compatibility_config"

    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        primaryjoin="and_(foreign(CompatibilityConfig.subgraph_name)==Subgraph.name)"
    )

    @classmethod
    def from_json(cls: Type["CompatibilityConfig"], json_data: Dict[str, Any],
                  subgraph: "Subgraph", session: Session) -> "CompatibilityConfig":
        if json_data.get("kind") != "CompatibilityConfig":
            raise ValueError(f"Expected CompatibilityConfig, got {json_data.get('kind')}")

        compat = cls(
            subgraph_name=subgraph.name,
            target_date=datetime.strptime(json_data.get("date"), "%Y-%m-%d")
        )
        session.add(compat)
        session.flush()
        return compat

    def to_json(self) -> Dict[str, Any]:
        """
        Serialize the CompatibilityConfig object to JSON format matching its original structure.

        Returns:
            A dictionary representing the CompatibilityConfig in JSON format.
        """
        return {
            "kind": "CompatibilityConfig",
            "date": self.target_date.strftime("%Y-%m-%d")  # Format datetime object back into string
        }
