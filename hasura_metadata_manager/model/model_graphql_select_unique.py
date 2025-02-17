from typing import Dict, Any, Optional, Type, TYPE_CHECKING, List

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .model_graphql_subscription_config import \
    ModelGraphQLSubscriptionConfig
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .model_graphql_config import ModelGraphQLConfig
    from ..object_type.field import ObjectField


class ModelGraphQLSelectUniqueField(Base):
    __tablename__ = "model_graphql_select_unique_field"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    select_unique_identifier: Mapped[str] = mapped_column(String(255), primary_key=True)
    field_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    model_graphql_select_unique: Mapped["ModelGraphQLSelectUnique"] = TemporalRelationship(
        "ModelGraphQLSelectUnique",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
                foreign(ModelGraphQLSelectUniqueField.subgraph_name) == ModelGraphQLSelectUnique.subgraph_name,
                foreign(ModelGraphQLSelectUniqueField.model_name) == ModelGraphQLSelectUnique.model_name,
                foreign(ModelGraphQLSelectUniqueField.select_unique_identifier) == ModelGraphQLSelectUnique.identifier
            )"""
    )

    object_field: Mapped["ObjectField"] = TemporalRelationship(
        "ObjectField",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelGraphQLSelectUniqueField.subgraph_name) == ObjectField.subgraph_name,
            foreign(ModelGraphQLSelectUniqueField.model_name) == ObjectField.object_type_name,
            foreign(ModelGraphQLSelectUniqueField.field_name) == ObjectField.logical_field_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["ModelGraphQLSelectUniqueField"], field_name: str,
                  model_name: str, subgraph_name: str,
                  select_unique_identifier: str) -> "ModelGraphQLSelectUniqueField":
        return cls(
            field_name=field_name,
            model_name=model_name,
            subgraph_name=subgraph_name,
            select_unique_identifier=select_unique_identifier
        )


def to_json(self) -> str:
    return self.field_name


class ModelGraphQLSelectUnique(Base):
    __tablename__ = "model_graphql_select_unique"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    identifier: Mapped[str] = mapped_column(String(255), primary_key=True)

    deprecated: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    query_root_field: Mapped[str] = mapped_column(String(255))
    subscription_root_field: Mapped[str] = mapped_column(String(255))
    subscription_polling_interval_ms: Mapped[int] = mapped_column(Integer)

    # Add relationship to unique fields
    unique_fields: Mapped[List["ModelGraphQLSelectUniqueField"]] = TemporalRelationship(
        "ModelGraphQLSelectUniqueField",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelGraphQLSelectUnique.subgraph_name) == ModelGraphQLSelectUniqueField.subgraph_name,
            foreign(ModelGraphQLSelectUnique.model_name) == ModelGraphQLSelectUniqueField.model_name,
            foreign(ModelGraphQLSelectUnique.identifier) == ModelGraphQLSelectUniqueField.select_unique_identifier
        )"""
    )

    graphql_config: Mapped["ModelGraphQLConfig"] = TemporalRelationship(
        "ModelGraphQLConfig",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelGraphQLSelectUnique.model_name) == ModelGraphQLConfig.model_name, 
            foreign(ModelGraphQLSelectUnique.subgraph_name) == ModelGraphQLConfig.subgraph_name
        )""",
    )

    @classmethod
    def from_json(cls: Type["ModelGraphQLSelectUnique"], json_data: Dict[str, Any],
                  model_name: str, subgraph_name: str, identifier: str) -> "ModelGraphQLSelectUnique":
        subscription = ModelGraphQLSubscriptionConfig.from_json(json_data["subscription"])

        instance = cls(
            model_name=model_name,
            subgraph_name=subgraph_name,
            identifier=identifier,
            deprecated=json_data.get("deprecated"),
            description=json_data.get("description"),
            query_root_field=json_data["queryRootField"],
            subscription_root_field=subscription.root_field,
            subscription_polling_interval_ms=subscription.polling_interval_ms
        )

        # Create unique field instances separately
        for field_name in json_data.get("uniqueIdentifier", []):
            ModelGraphQLSelectUniqueField.from_json(
                field_name=field_name,
                model_name=model_name,
                subgraph_name=subgraph_name,
                select_unique_identifier=identifier
            )

        return instance

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
            "subscription": subscription.to_json(),
            "uniqueIdentifier": [field.to_json() for field in self.unique_fields]
        }
