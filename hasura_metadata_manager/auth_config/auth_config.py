from typing import Dict, Type, Any

from sqlalchemy.orm import Mapped, Session

from .auth_config_base import AuthConfig as BaseAuthConfig
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..subgraph.subgraph_base import Subgraph


class AuthConfig(BaseAuthConfig):
    """Represents authentication configuration"""
    __tablename__ = "auth_config"

    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        primaryjoin="and_(foreign(AuthConfig.subgraph_name) == Subgraph.name)"
    )

    @classmethod
    def from_json(cls: Type["AuthConfig"], json_data: Dict[str, Any],
                  subgraph: "Subgraph", session: Session) -> "AuthConfig":
        if json_data.get("kind") != "AuthConfig":
            raise ValueError(f"Expected AuthConfig, got {json_data.get('kind')}")

        def_data = json_data.get("definition", {})
        mode_data = def_data.get("mode", {})
        mode_type = next(iter(mode_data.keys())) if mode_data else "unknown"
        mode_config = mode_data.get(mode_type, {})

        auth = cls(
            subgraph_name=subgraph.name,
            mode_type=mode_type,
            default_role=mode_config.get("role"),
            session_vars=mode_config.get("sessionVariables", {}),
            version=json_data.get("version", "v2")
        )
        session.add(auth)
        session.flush()
        return auth

    def to_json(self) -> Dict[str, Any]:
        """
        Serialize the AuthConfig object to JSON format matching its original structure.

        Returns:
            A dictionary representing the AuthConfig in JSON format.
        """
        return {
            "kind": "AuthConfig",
            "version": self.version,
            "definition": {
                "mode": {
                    self.mode_type: {
                        "role": self.default_role,
                        "sessionVariables": self.session_vars
                    }
                }
            }
        }
