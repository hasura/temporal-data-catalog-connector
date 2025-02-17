import logging
from typing import Dict, Any
from typing import List, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from ....schema.collection.field.collection_field_base import \
    CollectionField as BaseCollectionField
from .....mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ....field_map import FieldMap
    from ....schema.collection import Collection
    from .... import DataConnector
    from ....type_definition.type_definition import TypeDefinition

logger = logging.getLogger(__name__)


class CollectionField(BaseCollectionField):
    """
    Represents a field in a collection.

    Each field has:
    - A composite primary key (collection_name, physical_field_name, connector_name, subgraph_name)
    - A type definition (with references to either scalar types or collections)
    - Optional description and nullability flag
    """
    __tablename__ = "collection_field"

    # Type definition relationship with complete natural key
    type_definition: Mapped["TypeDefinition"] = TemporalRelationship(
        "TypeDefinition",
        primaryjoin="""and_(
            foreign(CollectionField.type_definition_connector_name) == TypeDefinition.connector_name,
            foreign(CollectionField.type_definition_name) == TypeDefinition.name,
            foreign(CollectionField.type_definition_subgraph_name) == TypeDefinition.subgraph_name
        )"""
    )

    # Relationships
    collection: Mapped["Collection"] = TemporalRelationship(
        "Collection",
        primaryjoin="""and_(
            foreign(CollectionField.collection_name) == Collection.name,
            foreign(CollectionField.connector_name) == Collection.connector_name,
            foreign(CollectionField.subgraph_name) == Collection.subgraph_name
        )"""
    )

    field_maps: Mapped[List["FieldMap"]] = TemporalRelationship(
        "FieldMap",

        primaryjoin="""and_(
            foreign(FieldMap.collection_name) == CollectionField.collection_name,
            foreign(FieldMap.physical_field_name) == CollectionField.physical_field_name,
            foreign(FieldMap.connector_name) == CollectionField.connector_name,
            foreign(FieldMap.subgraph_name) == CollectionField.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls,
                  json_data: Dict[str, Any],
                  connector: "DataConnector",
                  collection: "Collection",
                  session: Session) -> "CollectionField":
        """
        Create a CollectionField from JSON data.

        Args:
            json_data: Dictionary containing field definition
            connector: DataConnector
            collection: Parent Collection instance
            session: SQLAlchemy session

        Returns:
            Created CollectionField instance
        """
        logger.debug(f"Creating field {json_data.get('name')} for collection {collection.name}")

        type_info = json_data.get("type_info", {})

        # Create type definition
        from ....type_definition.type_definition import TypeDefinition
        type_definition = TypeDefinition.from_json(type_info, connector.name, connector.subgraph_name, session)

        # Create and return the field
        field = cls(
            collection_name=collection.name,
            physical_field_name=json_data["name"],
            description=json_data.get("description"),
            type_definition_connector_name=type_definition.connector_name,
            type_definition_name=type_definition.name,
            type_definition_subgraph_name=type_definition.subgraph_name,
            connector_name=collection.connector_name,
            subgraph_name=collection.subgraph_name
        )
        session.add(field)
        session.flush()



        logger.debug(f"Created field {field.physical_field_name} for collection {collection.name}")
        return field

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the collection field to a JSON-compatible dictionary

        Returns:
            Dictionary containing field definition
        """

        result = {
            "name": self.physical_field_name,
            "type_info": self.type_definition.to_json()
        }
        if self.description:
            result["description"] = self.description

        return result

    def __repr__(self) -> str:
        """String representation of the CollectionField"""
        return (f"CollectionField(collection='{self.collection_name}', "
                f"field='{self.physical_field_name}', "
                f"type={self.type_definition})")
