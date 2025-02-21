from typing import Type, Dict, Any, List, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from .field.object_field import ObjectField
from .object_type_base import ObjectType as BaseObjectType
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..subgraph.subgraph import Subgraph
    from ..relationship import Relationship
    from ..model import Model


class ObjectType(BaseObjectType):
    __tablename__ = "object_type"

    fields: Mapped[List["ObjectField"]] = TemporalRelationship(
        "ObjectField",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ObjectType.name) == ObjectField.object_type_name,
            foreign(ObjectType.subgraph_name) == ObjectField.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    # Relationships from ObjectType to Relationship
    source_relationships: Mapped[List["Relationship"]] = TemporalRelationship(
        "Relationship",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ObjectType.name)==Relationship.source_type_name, 
            foreign(ObjectType.subgraph_name)==Relationship.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    target_relationships: Mapped[List["Relationship"]] = TemporalRelationship(
        "Relationship",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ObjectType.name)==Relationship.target_type_name, 
            foreign(ObjectType.subgraph_name)==Relationship.target_subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(ObjectType.subgraph_name)==Subgraph.name)"
    )

    model: Mapped["Model"] = TemporalRelationship(
        "Model",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ObjectType.name)==Model.object_type_name,
            foreign(ObjectType.subgraph_name)==Model.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["ObjectType"], json_data: Dict[str, Any], subgraph: "Subgraph",
                  session: Session) -> "ObjectType":
        """Create an ObjectType from JSON data."""
        if json_data.get("kind") != "ObjectType":
            raise ValueError(f"Expected ObjectType, got {json_data.get('kind')}")

        def_data = json_data.get("definition", {})

        # Get connector mapping info
        connector_mapping = def_data.get("dataConnectorTypeMapping", [{}])[0]
        connector_name = connector_mapping.get("dataConnectorName")
        connector_obj_type = connector_mapping.get("dataConnectorObjectType")
        field_mapping = connector_mapping.get("fieldMapping", {})

        # Create or update object type (TemporalMixin will handle versioning)
        object_type = cls(
            name=def_data.get("name"),
            connector_name=connector_name,
            collection_type=connector_obj_type,
            field_mapping=field_mapping,
            subgraph_name=subgraph.name,
            description=def_data.get("description"),
            graphql_type_name=def_data.get("graphql", {}).get("typeName", def_data.get("name")),
            graphql_input_type_name=def_data.get("graphql", {}).get("inputTypeName")
        )
        session.add(object_type)

        session.flush()

        # Create new fields or update existing ones from field_mapping
        if "fields" in def_data:
            for field_data in def_data["fields"]:
                ObjectField.from_json(field_data, object_type, session)

        return object_type

    def to_json(self) -> dict:
        """Convert ObjectType to JSON representation matching hasura_metadata_manager format."""
        fields_data = [field.to_json() for field in self.fields if not field.t_is_deleted]

        definition = {
            "dataConnectorTypeMapping": [
                {
                    "dataConnectorName": self.connector_name,
                    "dataConnectorObjectType": self.collection_type,
                    "fieldMapping": self.field_mapping or {}
                }
            ],
            "description": self.description,
            "fields": fields_data,
            "globalIdFields": None,  # Not used in current implementation
            "graphql": {
                "apolloFederation": None,  # Not used in current implementation
                "inputTypeName": self.graphql_input_type_name,
                "typeName": self.graphql_type_name
            },
            "name": self.name
        }

        return {
            "definition": definition,
            "kind": "ObjectType",
            "version": "v1"
        }
