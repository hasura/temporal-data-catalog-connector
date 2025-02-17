from typing import Dict, Any, Optional, List, Type, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .model_graphql_aggregate_config import ModelGraphQLAggregateConfig
from .model_graphql_select_many_config import ModelGraphQLSelectManyConfig
from .model_graphql_select_unique import ModelGraphQLSelectUnique
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..model import Model


class ModelGraphQLConfig(Base):
    __tablename__ = "model_graphql_config"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    filter_input_type_name: Mapped[str] = mapped_column(String(255))
    order_by_expression_type: Mapped[str] = mapped_column(String(255), nullable=True)
    arguments_input_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    apollo_federation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    aggregate_config: Mapped["ModelGraphQLAggregateConfig"] = TemporalRelationship(
        "ModelGraphQLAggregateConfig",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelGraphQLConfig.model_name) == ModelGraphQLAggregateConfig.model_name, 
            foreign(ModelGraphQLConfig.subgraph_name) == ModelGraphQLAggregateConfig.subgraph_name
        )"""
    )

    select_many_config: Mapped["ModelGraphQLSelectManyConfig"] = TemporalRelationship(
        "ModelGraphQLSelectManyConfig",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelGraphQLConfig.model_name) == ModelGraphQLSelectManyConfig.model_name, 
            foreign(ModelGraphQLConfig.subgraph_name) == ModelGraphQLSelectManyConfig.subgraph_name
        )""")

    select_uniques: Mapped[List["ModelGraphQLSelectUnique"]] = TemporalRelationship(
        "ModelGraphQLSelectUnique",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelGraphQLConfig.model_name) == ModelGraphQLSelectUnique.model_name, 
            foreign(ModelGraphQLConfig.subgraph_name) == ModelGraphQLSelectUnique.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    model: Mapped["Model"] = TemporalRelationship(
        "Model",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelGraphQLConfig.model_name) == Model.name, 
            foreign(ModelGraphQLConfig.subgraph_name) == Model.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["ModelGraphQLConfig"], json_data: Dict[str, Any],
                  model_name: str, subgraph_name: str, session: Session) -> "ModelGraphQLConfig":
        config = cls(
            model_name=model_name,
            subgraph_name=subgraph_name,
            filter_input_type_name=json_data.get("filterInputTypeName"),
            order_by_expression_type=json_data.get("orderByExpressionType"),
            arguments_input_type=json_data.get("argumentsInputType"),
            apollo_federation=json_data.get("apolloFederation")
        )
        session.add(config)
        session.flush()
        


        if "aggregate" in json_data:
            aggregate_config = ModelGraphQLAggregateConfig.from_json(
                json_data["aggregate"],
                model_name=model_name,
                subgraph_name=subgraph_name
            )
            session.add(aggregate_config)
            session.flush()
            


        if "selectMany" in json_data:
            select_many_config = ModelGraphQLSelectManyConfig.from_json(
                json_data["selectMany"],
                model_name=model_name,
                subgraph_name=subgraph_name
            )
            session.add(select_many_config)
            session.flush()
            


        for unique_data in json_data.get("selectUniques", []):
            unique_config = ModelGraphQLSelectUnique.from_json(
                unique_data,
                model_name=model_name,
                subgraph_name=subgraph_name,
                identifier=unique_data.get("queryRootField")
            )
            session.add(unique_config)
            session.flush()
            

        return config

    def to_json(self) -> Dict[str, Any]:
        data = {
            "filterInputTypeName": self.filter_input_type_name,
            "orderByExpressionType": self.order_by_expression_type,
            "argumentsInputType": self.arguments_input_type,
            "apolloFederation": self.apollo_federation,
            "selectUniques": []  # Initialize with empty list by default
        }

        # List of keys to exclude if their values are None
        exclude_keys = ["orderByExpressionType"]

        # Exclude keys from the list where values are None
        data = {k: v for k, v in data.items() if v is not None or k not in exclude_keys}

        if self.aggregate_config:
            data["aggregate"] = self.aggregate_config.to_json()

        if self.select_many_config:
            data["selectMany"] = self.select_many_config.to_json()

        if self.select_uniques:
            # Group by query_root_field since we split by identifier
            unique_configs: Dict[str, List[str]] = {}
            for unique in self.select_uniques:
                if unique.query_root_field not in unique_configs:
                    unique_configs[unique.query_root_field] = []
                unique_configs[unique.query_root_field].append(unique.identifier)

            data["selectUniques"] = \
                [
                    {**unique.to_json(), "uniqueIdentifier": identifiers}
                    for query_field, identifiers in unique_configs.items()
                    for unique in self.select_uniques
                    if unique.query_root_field == query_field
                ][:1]  # Take only first one since they're duplicated by identifier

        return data
