from typing import Dict, Any, Optional, Type, TYPE_CHECKING

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .model_graphql_subscription_config import \
    ModelGraphQLSubscriptionConfig
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .model_graphql_config import ModelGraphQLConfig


class ModelGraphQLSelectManyConfig(Base):
    __tablename__ = "model_graphql_select_many_config"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    deprecated: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    query_root_field: Mapped[str] = mapped_column(String(255))
    subscription_root_field: Mapped[str] = mapped_column(String(255))
    subscription_polling_interval_ms: Mapped[int] = mapped_column(Integer)

    graphql_config: Mapped["ModelGraphQLConfig"] = TemporalRelationship(
        "ModelGraphQLConfig",
        uselist=False,
        primaryjoin="""and_(
            foreign(ModelGraphQLSelectManyConfig.model_name) == ModelGraphQLConfig.model_name, 
            foreign(ModelGraphQLSelectManyConfig.subgraph_name) == ModelGraphQLConfig.subgraph_name
        )""",
    )

    @classmethod
    def from_json(cls: Type["ModelGraphQLSelectManyConfig"], json_data: Dict[str, Any],
                  model_name: str, subgraph_name: str) -> "ModelGraphQLSelectManyConfig":
        subscription = ModelGraphQLSubscriptionConfig.from_json(json_data["subscription"])

        return cls(
            model_name=model_name,
            subgraph_name=subgraph_name,
            deprecated=json_data.get("deprecated", False),
            description=json_data.get("description"),
            query_root_field=json_data["queryRootField"],
            subscription_root_field=subscription.root_field,
            subscription_polling_interval_ms=subscription.polling_interval_ms
        )

    def to_json(self) -> Dict[str, Any]:
        subscription = ModelGraphQLSubscriptionConfig(
            deprecated=self.deprecated,
            description=self.description,
            polling_interval_ms=self.subscription_polling_interval_ms,
            root_field=self.subscription_root_field
        )

        return {
            "deprecated": self.deprecated,
            "description": self.description,
            "queryRootField": self.query_root_field,
            "subscription": subscription.to_json()
        }
