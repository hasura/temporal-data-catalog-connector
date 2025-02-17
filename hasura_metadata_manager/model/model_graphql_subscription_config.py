from typing import Dict, Any, Optional


class ModelGraphQLSubscriptionConfig:
    """Value object for subscription configuration"""

    def __init__(self, deprecated: Optional[str], description: Optional[str],
                 polling_interval_ms: int, root_field: str):
        self.deprecated = deprecated
        self.description = description
        self.polling_interval_ms = polling_interval_ms
        self.root_field = root_field

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "ModelGraphQLSubscriptionConfig":
        return cls(
            deprecated=json_data.get("deprecated"),
            description=json_data.get("description"),
            polling_interval_ms=json_data["pollingIntervalMs"],
            root_field=json_data["rootField"]
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "deprecated": self.deprecated,
            "description": self.description,
            "pollingIntervalMs": self.polling_interval_ms,
            "rootField": self.root_field
        }
