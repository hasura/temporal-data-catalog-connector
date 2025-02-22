from typing import Optional, List, Type, Dict, Any, TYPE_CHECKING, cast

from sqlalchemy.orm import Mapped, Session

from ...schema.collection.collection_base import Collection as BaseCollection
from ...schema.collection.collection_foreign_key import CollectionForeignKey
from ...schema.collection.collection_uniqueness_constraint import \
    CollectionUniquenessConstraint
from ...schema.collection.field.collection_field import CollectionField
from ....mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ...data_connector import DataConnector
    from ....model import Model
    from ....object_type import ObjectType

import logging

logger = logging.getLogger(__name__)


class Collection(BaseCollection):
    """Implementation class for Collection that includes relationships and methods."""
    __tablename__ = "collection"

    data_connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Collection.connector_name) == DataConnector.name, 
            foreign(Collection.subgraph_name) == DataConnector.subgraph_name
        )"""
    )
    object_type: Mapped[Optional["ObjectType"]] = TemporalRelationship(
        "ObjectType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Collection.object_type_name) == ObjectType.name, 
            foreign(Collection.connector_name) == ObjectType.connector_name, 
            foreign(Collection.subgraph_name) == ObjectType.subgraph_name
        )"""
    )
    model: Mapped[Optional["Model"]] = TemporalRelationship(
        "Model",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Collection.model_name) == Model.name, 
            foreign(Collection.subgraph_name) == Model.subgraph_name
        )"""
    )

    fields: Mapped[List["CollectionField"]] = TemporalRelationship(
        "CollectionField",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(CollectionField.collection_name) == Collection.name,
            foreign(CollectionField.connector_name) == Collection.connector_name,
            foreign(CollectionField.subgraph_name) == Collection.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    uniqueness_constraints: Mapped[List["CollectionUniquenessConstraint"]] = TemporalRelationship(
        "CollectionUniquenessConstraint",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(CollectionUniquenessConstraint.collection_name) == Collection.name,
            foreign(CollectionUniquenessConstraint.connector_name) == Collection.connector_name,
            foreign(CollectionUniquenessConstraint.subgraph_name) == Collection.subgraph_name
        )""",
        info={'skip_constraint': True}
    )
    foreign_keys: Mapped[List["CollectionForeignKey"]] = TemporalRelationship(
        "CollectionForeignKey",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(CollectionForeignKey.collection_name) == Collection.name,
            foreign(CollectionForeignKey.connector_name) == Collection.connector_name,
            foreign(CollectionForeignKey.subgraph_name) == Collection.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["Collection"], json_data: Dict[str, Any], data_connector: "DataConnector",
                  session: Session) -> "Collection":
        """Create a Collection from JSON data."""
        logger.debug(f"Creating Collection: {json_data.get('name')}")

        if not json_data.get("name"):
            raise ValueError("Collection name is required")

        name = json_data.get("name")

        existing_collection = cast(Collection, session.query(cls).filter_by(
            name=name,
            subgraph_name=data_connector.subgraph_name,
            connector_name=data_connector.name
        ).first())

        if not existing_collection:
            collection = cls(
                name=name,
                connector_name=data_connector.name,
                subgraph_name=data_connector.subgraph_name,
                description=json_data.get("description"),
                object_type_name=json_data.get("object_type_name"),
                model_name=json_data.get("object_type_name"),
                physical_collection_name=json_data.get("arguments", {}).get("collection", json_data["name"])
            )
            session.add(collection)
            session.flush()  # Added flush after collection creation

        else:
            session.add(existing_collection)
            session.flush()
            logger.warning(f"Collection with name {json_data.get('name')} already exists")
            return existing_collection

        # Process fields if present
        field_types = json_data.get("field_types", {})
        if field_types:
            field_count = 0
            for field_name, field_type_info in field_types.items():
                try:
                    field_data = {
                        "name": field_name,
                        "type_info": field_type_info,
                        "description": field_type_info.get("description")
                    }
                    CollectionField.from_json(field_data, data_connector, collection, session)
                    field_count += 1
                    if field_count % 50 == 0:  # Flush every 50 fields
                        session.flush()
                        session.expire_all()
                except Exception as e:
                    logger.error(f"Error processing field {field_name}: {str(e)}")
                    raise

            session.flush()  # make sure collection fields are committed so we can associate FKs with them

            # Handle foreign keys
            fk_count = 0
            for fk_name, fk_data in json_data.get("foreign_keys", {}).items():
                try:
                    logger.debug(f"Processing Foreign Key: {fk_name}, Data: {fk_data}")

                    # Ensure the function can handle multiple column mappings
                    CollectionForeignKey.from_json(
                        fk_name=fk_name,
                        fk_data=fk_data,
                        collection=collection,
                        session=session
                    )
                    fk_count += 1
                    if fk_count % 50 == 0:  # Flush every 50 foreign keys
                        session.flush()
                        session.expire_all()
                except Exception as e:
                    logger.error(f"Error processing foreign key {fk_name}: {str(e)}")
                    raise

            # Handle uniqueness constraints (unchanged)
            constraint_count = 0
            for constraint_name, constraint_data in json_data.get("uniqueness_constraints", {}).items():
                try:
                    CollectionUniquenessConstraint.from_json(
                        constraint_name=constraint_name,
                        constraint_data=constraint_data,
                        collection=collection,
                        session=session
                    )
                    constraint_count += 1
                    if constraint_count % 50 == 0:  # Flush every 50 constraints
                        session.flush()
                        session.expire_all()
                except Exception as e:
                    logger.error(f"Error processing uniqueness constraint {constraint_name}: {str(e)}")
                    raise

            session.flush()  # Final flush after all constraints

        session.flush()
        return collection

    def to_json(self) -> Dict[str, Any]:
        """Convert the collection to a JSON-compatible dictionary."""
        logger.debug(f"Converting Collection to JSON: {self.name}")

        json_data = {
            "name": self.name,
            "description": self.description,
            "object_type_name": self.object_type_name,
            "arguments": {
                "collection": self.physical_collection_name
            },
            "field_types": {
                field.physical_field_name: field.to_json()
                for field in self.fields
            }
        }

        # Use CollectionForeignKey's class method for serialization
        foreign_keys_dict = CollectionForeignKey.serialize_foreign_keys(self.foreign_keys)
        if foreign_keys_dict:
            json_data["foreign_keys"] = foreign_keys_dict

        # Add uniqueness constraints
        constraints_dict = {
            constraint.constraint_name: constraint.to_json()
            for constraint in self.uniqueness_constraints
        }
        if constraints_dict:
            json_data["uniqueness_constraints"] = constraints_dict

        logger.debug(f"Converted Collection to JSON: {json_data}")
        return json_data

    def add_field(self, field_name: str, description: Optional[str] = None) -> CollectionField:
        """
        Add a new field to the collection

        Args:
            field_name: Name of the field
            description: Optional field description

        Returns:
            Created CollectionField instance

        Raises:
            ValueError: If field already exists
        """
        logger.debug(f"Adding field {field_name} to Collection {self.name}")

        if self.get_field(field_name):
            raise ValueError(f"Field {field_name} already exists in collection {self.name}")

        field = CollectionField(
            collection_name=self.name,
            physical_field_name=field_name,
            connector_name=self.connector_name,
            subgraph_name=self.subgraph_name,
            description=description
        )
        self.fields.append(field)
        logger.debug(f"Added field {field_name} to Collection {self.name}")
        return field

    def get_field(self, field_name: str) -> Optional[CollectionField]:
        """
        Get a field by name

        Args:
            field_name: Name of the field to retrieve

        Returns:
            CollectionField if found, None otherwise
        """
        return next((field for field in self.fields
                     if field.physical_field_name == field_name), None)

    def remove_field(self, field_name: str) -> bool:
        """
        Remove a field from the collection

        Args:
            field_name: Name of the field to remove

        Returns:
            True if field was removed, False if not found
        """
        logger.debug(f"Removing field {field_name} from Collection {self.name}")
        field = self.get_field(field_name)
        if field:
            self.fields.remove(field)
            logger.debug(f"Removed field {field_name} from Collection {self.name}")
            return True
        return False

    def update_field(self, field_name: str, **kwargs) -> Optional[CollectionField]:
        """
        Update a field's attributes

        Args:
            field_name: Name of the field to update
            **kwargs: Attributes to update

        Returns:
            Updated CollectionField if found, None otherwise
        """
        logger.debug(f"Updating field {field_name} in Collection {self.name}")
        field = self.get_field(field_name)
        if field:
            for key, value in kwargs.items():
                if hasattr(field, key):
                    setattr(field, key, value)
            logger.debug(f"Updated field {field_name} in Collection {self.name}")
            return field
        return None

    def validate(self) -> bool:
        """
        Validate the collection configuration

        Returns:
            True if valid, raises ValueError if invalid
        """
        logger.debug(f"Validating Collection {self.name}")

        if not self.name:
            raise ValueError("Collection name is required")

        if not self.physical_collection_name:
            raise ValueError("Physical collection name is required")

        if not self.fields:
            raise ValueError("Collection must have at least one field")

        logger.debug(f"Collection {self.name} is valid")
        return True

    def __repr__(self) -> str:
        """String representation of the Collection"""
        return (f"Collection(name='{self.name}', "
                f"connector='{self.connector_name}', "
                f"object_type='{self.object_type_name}')")
