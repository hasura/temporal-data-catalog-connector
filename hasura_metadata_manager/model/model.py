from typing import TYPE_CHECKING

from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..subgraph.subgraph import Subgraph

from typing import List, Type, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from .model_base import Model as BaseModel
from .orderable_field.model_orderable_field import ModelOrderableField
from .model_argument import ModelArgument
from .model_graphql_config import ModelGraphQLConfig
from .model_source_config import ModelSourceConfig
from ..model_permission.model_permission_base import ModelPermission
from ..object_type.object_type import ObjectType

if TYPE_CHECKING:
    from ..subgraph.subgraph import Subgraph


class Model(BaseModel):
    __tablename__ = "model"

    # Relationships
    object_type: Mapped["ObjectType"] = TemporalRelationship(
        "ObjectType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Model.object_type_name)==ObjectType.name, 
            foreign(Model.subgraph_name)==ObjectType.subgraph_name
        )"""
    )
    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(Model.subgraph_name)==Subgraph.name)")
    orderable_fields: Mapped[List["ModelOrderableField"]] = TemporalRelationship(
        "ModelOrderableField",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Model.name)==ModelOrderableField.model_name, 
            foreign(Model.subgraph_name)==ModelOrderableField.subgraph_name
        )""",
        info={'skip_constraint': True}
    )
    arguments: Mapped[List["ModelArgument"]] = TemporalRelationship(
        "ModelArgument",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Model.name)==ModelArgument.model_name, 
            foreign(Model.subgraph_name)==ModelArgument.subgraph_name
        )""",
        info={'skip_constraint': True}
    )
    permissions: Mapped[List["ModelPermission"]] = TemporalRelationship(
        "ModelPermission",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Model.name)==ModelPermission.model_name, 
            foreign(Model.subgraph_name)==ModelPermission.subgraph_name
        )""",
        info={'skip_constraint': True}
    )
    graphql_config: Mapped["ModelGraphQLConfig"] = TemporalRelationship(
        "ModelGraphQLConfig",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Model.name)==ModelGraphQLConfig.model_name, 
            foreign(Model.subgraph_name)==ModelGraphQLConfig.subgraph_name
        )"""
    )
    source_config: Mapped["ModelSourceConfig"] = TemporalRelationship(
        "ModelSourceConfig",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Model.name)==ModelSourceConfig.model_name, 
            foreign(Model.subgraph_name)==ModelSourceConfig.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["Model"], json_data: Dict[str, Any], subgraph: "Subgraph", session: Session) -> "Model":
        """Create a Model from JSON data."""
        def_data = json_data["definition"]

        model = cls(
            name=def_data["name"],
            object_type_name=def_data["objectType"],
            subgraph_name=subgraph.name,
            aggregate_expression=def_data.get("aggregateExpression", "default"),
            filter_expression_type=def_data.get("filterExpressionType", "default"),
            global_id_source=def_data.get("globalIdSource", False),
            description=def_data.get("description")
        )
        session.add(model)
        session.flush()
        


        # Create orderable fields
        if "orderableFields" in def_data:
            for field_data in def_data["orderableFields"]:
                orderable_field = ModelOrderableField(
                    field_name=field_data["fieldName"],
                    enable_all_directions=field_data["orderByDirections"]["enableAll"],
                    model_name=model.name,
                    subgraph_name=model.subgraph_name
                )
                session.add(orderable_field)
                session.flush()
                


        # Create arguments
        if "arguments" in def_data:
            for arg_data in def_data["arguments"]:
                argument = ModelArgument.from_json(
                    arg_data,
                    model_name=model.name,
                    subgraph_name=model.subgraph_name
                )
                argument.model = model
                session.add(argument)
                session.flush()
                


        # Create GraphQL config
        if "graphql" in def_data:
            graphql_config = ModelGraphQLConfig.from_json(
                def_data["graphql"],
                model_name=model.name,
                subgraph_name=model.subgraph_name,
                session=session
            )
            graphql_config.model = model

        # Create source config
        if "source" in def_data:
            source_config = ModelSourceConfig.from_json(
                def_data["source"],
                model_name=model.name,
                subgraph_name=model.subgraph_name,
                session=session
            )
            source_config.model = model

        return model

    def to_json(self) -> Dict[str, Any]:
        """Convert the model to a JSON-compatible dictionary."""
        definition = {
            "name": self.name,
            "objectType": self.object_type_name,
            "aggregateExpression": self.aggregate_expression,
            "filterExpressionType": self.filter_expression_type,
            "globalIdSource": self.global_id_source,
            "description": self.description,
            "arguments": []
        }

        # Add orderable fields
        if self.orderable_fields:
            definition["orderableFields"] = [
                {
                    "fieldName": field.field_name,
                    "orderByDirections": {
                        "enableAll": field.enable_all_directions
                    }
                }
                for field in self.orderable_fields
            ]

        # Add arguments
        if self.arguments:
            definition["arguments"] = [arg.to_json() for arg in self.arguments]

        # Add GraphQL config
        if self.graphql_config:
            definition["graphql"] = self.graphql_config.to_json()

        # Add source config
        if self.source_config:
            definition["source"] = self.source_config.to_json()

        return {
            "definition": definition,
            "kind": "Model",
            "version": "v1"
        }
