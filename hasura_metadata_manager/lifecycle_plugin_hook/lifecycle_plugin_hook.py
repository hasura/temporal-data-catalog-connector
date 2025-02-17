from typing import Dict, Type, Any

from sqlalchemy.orm import Mapped, Session

from .lifecycle_plugin_hook_base import LifecyclePluginHook as BaseLifecyclePluginHook
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..subgraph.subgraph_base import Subgraph


class LifecyclePluginHook(BaseLifecyclePluginHook):
    """Represents a lifecycle plugin hook configuration"""
    __tablename__ = "lifecycle_plugin_hook"

    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        primaryjoin="and_(foreign(LifecyclePluginHook.subgraph_name)==Subgraph.name)"
    )

    @classmethod
    def from_json(cls: Type["LifecyclePluginHook"], json_data: Dict[str, Any],
                  subgraph: "Subgraph", session: Session) -> "LifecyclePluginHook":
        if json_data.get("kind") != "LifecyclePluginHook":
            raise ValueError(f"Expected LifecyclePluginHook, got {json_data.get('kind')}")

        def_data = json_data.get("definition", {})
        hook = cls(
            name=def_data["name"],
            subgraph_name=subgraph.name,
            url=def_data.get("url", {}).get("value"),
            pre_hook=def_data.get("pre") == "request",
            config=def_data.get("config", {}),
            version=json_data.get("version", "v1")
        )
        session.add(hook)
        session.flush()

        return hook

    def to_json(self) -> Dict[str, Any]:
        """
        Serialize the LifecyclePluginHook object back to the JSON format matching its original structure.
        Returns:
            A dictionary representation of the LifecyclePluginHook in JSON format.
        """
        return {
            "kind": "LifecyclePluginHook",
            "version": self.version,
            "definition": {
                "name": self.name,
                "pre": "request" if self.pre_hook else "response",
                "url": {
                    "value": self.url
                },
                "config": self.config  # Assuming `self.config` already holds the dictionary in the structure you want
            }
        }
