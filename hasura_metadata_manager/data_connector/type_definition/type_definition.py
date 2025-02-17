import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy.orm import Session

from ..scalar_type import ConnectorScalarType
from ..type_definition.type_definition_base import TypeDefinition as BaseTypeDefinition, \
    TypeDefinitionKind
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def generate_name(type_definition: dict) -> str:
    """
    Generate a name based on the given type definition structure.

    :param type_definition: The dictionary defining the type structure.
    :return: A string representation of the type name.
    """

    try:
        # If the type is named, and it has a 'name' key, return the name
        if type_definition.get("type") == "named" and "name" in type_definition:
            name = type_definition["name"]
            return f"{name}!"  # named types are always non-nullable

        # If the type is nullable, handle its underlying type
        if type_definition.get("type") == "nullable" and "underlying_type" in type_definition:
            # Recursively parse the underlying type
            underlying_name = generate_name(type_definition["underlying_type"]).rstrip('!')
            # Mark this as nullable
            return f"{underlying_name}!!"

        # If the type is an array, handle the element type
        if type_definition.get("type") == "array" and "element_type" in type_definition:
            # Recursively parse the element type
            element_name = generate_name(type_definition["element_type"])
            # Wrap in array brackets
            return f"[{element_name}]"

        # If the type is predicate, handle the element type
        if type_definition.get("type") == "predicate" and "object_type_name" in type_definition:
            # Recursively parse the element type
            object_type_name = type_definition["object_type_name"]
            # Wrap in array brackets
            return f"{object_type_name}!"

        # Default case: Unsupported type
        raise ValueError(f"Unsupported type definition: {type_definition}")

    except Exception as e:
        logger.error(f"Error extracting type definition name: {str(e)}")
        raise ValueError(f"Error extracting type definition name: {type_definition}")


class TypeDefinition(BaseTypeDefinition):
    """
    Full implementation of TypeDefinition with nested type support and natural keys.
    Supports relationships with BooleanExpressionType, AggregateFunctions, and DataConnectorScalar.
    """
    __tablename__ = "type_definition"

    child_type = TemporalRelationship(
        "TypeDefinition",
        primaryjoin="""and_(
            foreign(TypeDefinition.subgraph_name)==TypeDefinition.subgraph_name, 
            foreign(TypeDefinition.connector_name)==TypeDefinition.connector_name, 
            foreign(TypeDefinition.child_type_name)==TypeDefinition.name
        )""",
        remote_side="[TypeDefinition.subgraph_name, TypeDefinition.connector_name, TypeDefinition.name]",
        uselist=False
    )

    @classmethod
    def from_json(cls, type_info: Dict[str, Any], connector_name: str,
                  subgraph_name: Optional[str] = None,
                  session: Optional[Session] = None) -> "TypeDefinition":
        """
        Create a TypeDefinition from JSON, handling nested types with deduplication.

        Args:
            type_info: Dictionary containing type information
            connector_name: Name of the data connector
            subgraph_name: Name of the subgraph (optional)
            session: SQLAlchemy session for saving nested types

        Returns:
            TypeDefinition instance

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if session is None:
            raise ValueError("Session is required for creating TypeDefinition")

        # Extract core type information
        type_info = type_info.get('type')
        core_type = type_info.get('type')

        name = generate_name(type_info)
        if core_type == 'named':
            name = name.rstrip('!')

        if not name:
            raise ValueError("Type definition must have a name")

        # Check if type definition already exists
        existing_type: Optional[TypeDefinition] = session.query(cls).filter_by(
            type=core_type,
            name=name,
            connector_name=connector_name,
            subgraph_name=subgraph_name
        ).first()

        if existing_type:
            return existing_type

        # Handle nested types recursively
        if core_type == 'array':
            element_type_info = type_info.get('element_type', {})

            # make sure the element exists first...
            element = cls.from_json(
                {"type": element_type_info},
                connector_name=connector_name,
                subgraph_name=subgraph_name,
                session=session
            )

            # Create the element type
            type_def = cls(
                type=core_type,
                name=name,
                connector_name=connector_name,
                subgraph_name=subgraph_name,
                child_type_name=element.name
            )

            session.add(type_def)
            session.flush()


            return type_def

        elif core_type == 'nullable':

            underlying_type_info = type_info.get('underlying_type', {})

            # make sure the underlying exists first...
            underlying = cls.from_json(
                {"type": underlying_type_info},
                connector_name=connector_name,
                subgraph_name=subgraph_name,
                session=session
            )

            # now create the reference to the underlying
            type_def = cls(
                type=core_type,
                name=name,
                connector_name=connector_name,
                subgraph_name=subgraph_name,
                child_type_name=underlying.name
            )
            session.add(type_def)
            session.flush()


            return type_def
        else:  # named
            # First check if element exists as a scalar
            scalar = session.query(ConnectorScalarType).filter_by(
                name=name,
                connector_name=connector_name,
                subgraph_name=subgraph_name
            ).first()

            type_def = cls(
                type=core_type,
                name=name,
                connector_name=connector_name,
                subgraph_name=subgraph_name
            )

            if scalar:
                # If it's a scalar reference
                type_def.scalar_type_name = name
            else:
                # If not a scalar, assume it's a collection
                type_def.collection_type_name = name

            session.add(type_def)
            session.flush()


            return type_def

    def to_json(self, session: Optional[Session] = None) -> Dict[str, Any]:
        """
        Convert type definition to a JSON-compatible dictionary matching the schema format.
        Recursively processes child types if they exist.

        Args:
            session: SQLAlchemy session for loading related types

        Returns:
            Dictionary representation of the type definition that matches the expected schema:
            - For array types: {"type": "array", "element_type": {...}}
            - For nullable types: {"type": "nullable", "underlying_type": {...}}
            - For named types: {"type": "named", "name": "type_name"}
        """
        if self.type == TypeDefinitionKind.ARRAY.value:
            if not self.child_type_name:
                raise ValueError("Array type must have a child_type_name")

            # Get the child type definition
            child_type = self.child_type
            if child_type is None and session:
                child_type: Optional[TypeDefinition] = session.query(TypeDefinition).filter_by(
                    name=self.child_type_name,
                    connector_name=self.connector_name,
                    subgraph_name=self.subgraph_name
                ).first()

            if child_type is None:
                raise ValueError(f"Could not find child type: {self.child_type_name}")

            return {
                "type": "array",
                "element_type": child_type.to_json(session)
            }

        elif self.type == TypeDefinitionKind.NULLABLE.value:
            if not self.child_type_name:
                raise ValueError("Nullable type must have a child_type_name")

            # Get the child type definition
            child_type = self.child_type
            if child_type is None and session:
                child_type = session.query(TypeDefinition).filter_by(
                    name=self.child_type_name,
                    connector_name=self.connector_name,
                    subgraph_name=self.subgraph_name
                ).first()

            if child_type is None:
                raise ValueError(f"Could not find child type: {self.child_type_name}")

            return {
                "type": "nullable",
                "underlying_type": child_type.to_json(session)
            }

        elif self.type == TypeDefinitionKind.NAMED.value:
            # For named types, just return the basic structure
            return {
                "type": "named",
                "name": self.scalar_type_name or self.collection_type_name
            }

        elif self.type == TypeDefinitionKind.PREDICATE.value:
            # For named types, just return the basic structure
            return {
                "type": "predicate",
                "object_type_name": self.collection_type_name.rstrip("!").replace("[", "").replace("]", "")
            }

        else:
            raise ValueError(f"Unsupported type: {self.type}")

    def __repr__(self) -> str:
        """String representation of the TypeDefinition"""
        return (f"<TypeDefinition("
                f"type={self.type}, "
                f"name={self.name}, "
                f"subgraph_name={self.subgraph_name}, "
                f"connector_name={self.connector_name})>")
