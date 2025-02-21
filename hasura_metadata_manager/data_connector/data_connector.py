import json
import logging
from typing import List, Optional, Type, Dict, Any, Tuple, cast

from sqlalchemy.orm import Mapped, Session

from .argument_preset import ArgumentPreset
from .capability import RelationshipCapability, MutationCapability
from .capability.data_connector_capability import DataConnectorCapability
from .capability.query_capability import QueryCapability
from .comparison_operator import ComparisonOperator
from .data_connector_base import DataConnector as BaseDataConnector
from .field_map.field_map import FieldMap
from .function.function import Function
from .header import Header
from .procedure import Procedure
from .scalar_type.connector_scalar_type import ConnectorScalarType
from .schema.collection.collection import Collection
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..object_type.object_type import ObjectType
from ..subgraph.subgraph_base import Subgraph

logger = logging.getLogger(__name__)


class DataConnector(BaseDataConnector):
    """Implementation of the DataConnector class with relationships and JSON conversion capabilities."""

    __tablename__ = "data_connector"

    # Relationships to other entities
    object_types: Mapped[List["ObjectType"]] = TemporalRelationship(
        "ObjectType",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == ObjectType.subgraph_name,
            foreign(DataConnector.name) == ObjectType.connector_name
        )""",
        info={'skip_constraint': True}
    )

    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(foreign(DataConnector.subgraph_name) == Subgraph.name)"""
    )
    capabilities: Mapped[Optional["DataConnectorCapability"]] = TemporalRelationship(
        "DataConnectorCapability",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == DataConnectorCapability.subgraph_name,
            foreign(DataConnector.name) == DataConnectorCapability.connector_name
        )""",
        info={'skip_constraint': True}
    )
    collections: Mapped[List["Collection"]] = TemporalRelationship(
        "Collection",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == Collection.subgraph_name,
            foreign(DataConnector.name) == Collection.connector_name
        )""",
        info={'skip_constraint': True}
    )

    mutation_capability: Mapped["MutationCapability"] = TemporalRelationship(
        "MutationCapability",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == MutationCapability.subgraph_name,
            foreign(DataConnector.name) == MutationCapability.connector_name
        )"""
    )
    query_capability: Mapped["QueryCapability"] = TemporalRelationship(
        "QueryCapability",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == QueryCapability.subgraph_name,
            foreign(DataConnector.name) == QueryCapability.connector_name
        )"""
    )
    relationship_capability: Mapped["RelationshipCapability"] = TemporalRelationship(
        "RelationshipCapability",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == RelationshipCapability.subgraph_name,
            foreign(DataConnector.name) == RelationshipCapability.connector_name
        )"""
    )
    procedures: Mapped[List["Procedure"]] = TemporalRelationship(
        "Procedure",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == Procedure.subgraph_name,
            foreign(DataConnector.name) == Procedure.connector_name
        )""",
        info={'skip_constraint': True}
    )
    functions: Mapped[List["Function"]] = TemporalRelationship(
        "Function",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == Function.subgraph_name,
            foreign(DataConnector.name) == Function.connector_name
        )""",
        info={'skip_constraint': True}
    )
    scalar_types: Mapped[List["ConnectorScalarType"]] = TemporalRelationship(
        "ConnectorScalarType",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == ConnectorScalarType.subgraph_name,
            foreign(DataConnector.name) == ConnectorScalarType.connector_name
        )""",
        info={'skip_constraint': True}
    )
    comparison_operators: Mapped[List["ComparisonOperator"]] = TemporalRelationship(
        "ComparisonOperator",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == ComparisonOperator.subgraph_name,
            foreign(DataConnector.name) == ComparisonOperator.connector_name
        )""",
        info={'skip_constraint': True}
    )

    # Relationships to replace JSON columns
    argument_presets: Mapped[List["ArgumentPreset"]] = TemporalRelationship(
        "ArgumentPreset",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(DataConnector.subgraph_name) == ArgumentPreset.subgraph_name,
            foreign(DataConnector.name) == ArgumentPreset.connector_name
        )""",
        info={'skip_constraint': True}
    )

    headers: Mapped[List["Header"]] = TemporalRelationship(
        "Header",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            Header.connector_name == foreign(DataConnector.name),
            Header.subgraph_name == foreign(DataConnector.subgraph_name),
            Header.is_response_header == False
        )""",
        info={'skip_constraint': True}
    )

    response_headers: Mapped[List["Header"]] = TemporalRelationship(
        "Header",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            Header.connector_name == foreign(DataConnector.name),
            Header.subgraph_name == foreign(DataConnector.subgraph_name),
            Header.is_response_header == True
        )""",
        info={'skip_constraint': True}
    )

    def _process_field_mappings(
            self,
            _json_data: Dict[str, Any],
            session: Session
    ) -> List[Tuple[str, str, str, str]]:
        """
        Process field mappings for the data connector.

        Args:
            _json_data: Full JSON data for the data connector
            session: SQLAlchemy session

        Returns:
            List of tuples containing (object_type_name, logical_field_name, collection_name, physical_field_name)
        """
        field_mappings = []

        # Find all ObjectTypes for this connector and subgraph
        object_types = cast(List[ObjectType], session.query(ObjectType).filter_by(
            subgraph_name=self.subgraph_name,
            connector_name=self.name
        ).all())

        for object_type in object_types:
            # Check if the object type has a corresponding collection
            collection: Optional[Collection] = session.query(Collection).filter_by(
                object_type_name=object_type.name,
                connector_name=self.name,
                subgraph_name=self.subgraph_name
            ).first()

            if not collection:
                logger.warning(f"No collection found for object type {object_type.name}")
                continue

            # Collect field mappings for this object type
            for logical_field_name, physical_mapping in object_type.field_mapping.items():
                field_mappings.append((
                    object_type.name,  # object type name
                    logical_field_name,  # logical field name
                    collection.name,  # collection name
                    physical_mapping["column"]["name"]  # physical field name
                ))

        return field_mappings

    def _create_field_maps(
            self,
            field_mappings: List[Tuple[str, str, str, str]],
            session: Session
    ) -> None:
        """
        Create FieldMap entries for the given mappings.

        Args:
            field_mappings: List of (object_type_name, logical_field_name, collection_name, physical_field_name) tuples
            session: SQLAlchemy session
        """
        for obj_type_name, logical_name, coll_name, physical_name in field_mappings:
            # First verify that the object type exists
            object_type = session.query(ObjectType).filter_by(
                name=obj_type_name,
                subgraph_name=self.subgraph_name
            ).first()

            if not object_type:
                logger.warning(f"Object type {obj_type_name} not found, skipping field map")
                continue

            # Verify the collection exists
            collection = session.query(Collection).filter_by(
                name=coll_name,
                connector_name=self.name,
                subgraph_name=self.subgraph_name
            ).first()

            if not collection:
                logger.warning(f"Collection {coll_name} not found, skipping field map")
                continue

            # Create the field map
            field_map = FieldMap(
                collection_name=coll_name,
                physical_field_name=physical_name,
                object_type_name=obj_type_name,
                subgraph_name=self.subgraph_name,
                logical_field_name=logical_name,
                connector_name=self.name,
            )

            session.add(field_map)
            session.flush()


        try:
            session.flush()
        except Exception as e:
            logger.error(f"Error creating field maps: {str(e)}")
            raise

    def _convert_json_to_models(self, json_data: dict, session: Session) -> None:
        """
        Convert JSON data to related model instances.

        Args:
            json_data: Dictionary containing the JSON data
            session: SQLAlchemy session
        """
        # Convert argument presets
        if 'argumentPresets' in json_data:
            for preset in json_data.get('argumentPresets', {}):
                arg_preset = ArgumentPreset(
                    connector_name=self.name,
                    subgraph_name=self.subgraph_name,
                    name=preset.get('name'),
                    value=str(preset.get('value')),
                    argument_type=preset.get('type')
                )
                session.add(arg_preset)
                session.flush()


        # Convert headers
        if json_data.get('headers'):
            for key, value in json_data.get('headers', {}).items():
                header = Header(
                    connector_name=self.name,
                    subgraph_name=self.subgraph_name,
                    key=key,
                    value=json.dumps(value) if value else None,
                    is_response_header=False
                )
                session.add(header)
                session.flush()


        # Convert response headers
        if json_data.get('responseHeaders'):
            for key, value in json_data['responseHeaders'].items():
                response_header = Header(
                    connector_name=self.name,
                    subgraph_name=self.subgraph_name,
                    key=key,
                    value=json.dumps(value) if value else None,
                    is_response_header=True
                )
                session.add(response_header)
                session.flush()


    def _convert_models_to_json(self) -> dict:
        """
        Convert related models back to JSON format.

        Returns:
            Dictionary containing the JSON representation of the related models
        """
        result = {
            'argumentPresets': [
                {
                    'name': preset.name,
                    'value': preset.value,
                    'type': preset.argument_type
                }
                for preset in self.argument_presets
            ],
            'headers': {
                header.key: json.loads(header.value)
                for header in self.headers
            } if self.headers else None,
            'responseHeaders': {
                header.key: json.loads(header.value)
                for header in self.response_headers
            } if self.response_headers else None}

        return result

    @classmethod
    def from_json(cls: Type["DataConnector"], json_data: Dict[str, Any], subgraph: "Subgraph",
                  session: Session) -> "DataConnector":
        """Create a DataConnector and all its related entities from JSON data."""
        logger.debug("Starting DataConnector import")
        if json_data.get("kind") != "DataConnectorLink":
            raise ValueError(f"Expected DataConnectorLink, got {json_data.get('kind')}")

        def_data = json_data.get("definition", {})
        url_data = def_data.get("url", {})
        outer_schema_data = def_data.get("schema", {})
        schema_data = outer_schema_data.get("schema", {})

        # Extract URLs based on format
        read_url = write_url = None
        if "readWriteUrls" in url_data:
            urls = url_data["readWriteUrls"]
            read_url = urls.get("read", {}).get("value")
            write_url = urls.get("write", {}).get("value")
        elif "value" in url_data:
            read_url = write_url = url_data["value"]

        if not read_url or not write_url:
            raise ValueError("Missing required URL configuration")

        # Include optional fields
        connector = cls(
            name=def_data.get("name", "default"),
            subgraph_name=subgraph.name,
            read_url=read_url,
            write_url=write_url,
            schema_version=def_data.get('schema', {}).get('version')
        )
        session.add(connector)
        session.flush()


        # Convert JSON data to related models
        connector._convert_json_to_models(def_data, session)
        session.flush()

        # 1. Process scalar types first
        if "scalar_types" in schema_data:
            logger.debug("Processing connector scalar types")
            for scalar_name, scalar_data in schema_data["scalar_types"].items():
                try:
                    ConnectorScalarType.from_json(scalar_name, scalar_data, connector, session)
                except Exception as e:
                    logger.error(f"Error processing scalar type {scalar_name}: {str(e)}")
                    raise
        session.flush()

        # 2. Process capabilities
        if "capabilities" in outer_schema_data:
            logger.debug("Processing capabilities")
            caps_data = outer_schema_data["capabilities"]
            DataConnectorCapability.from_json(caps_data, connector, session)
        session.flush()

        # 3. Create collections
        logger.debug("Processing collections")
        collections = []

        # Process object types in the schema
        for type_name, type_data in schema_data.get("object_types", {}).items():
            # Try to find a matching ObjectType
            object_type = session.query(ObjectType).filter_by(
                subgraph_name=subgraph.name,
                connector_name=connector.name,
                collection_type=type_name
            ).first()

            # Set logical_name based on existing ObjectType, or use type_name
            logical_name = object_type.name if object_type else None

            # Find the corresponding collection definition
            collection_definition = next(
                (coll for coll in schema_data.get("collections", []) if coll['name'] == type_name),
                None
            )

            try:
                collection_data = {
                    "name": type_name,  # Physical name from schema
                    "object_type_name": logical_name,  # Will be None if no matching ObjectType
                    "field_types": type_data.get("fields", {}),
                    "description": type_data.get("description")
                }

                # Add the entire collection definition if available
                if collection_definition:
                    # Add all key-value pairs from the collection definition
                    for key, value in collection_definition.items():
                        if key != 'name':  # Exclude 'name' as it's already set
                            collection_data[key] = value

                collection = Collection.from_json(collection_data, connector, session)
                collections.append(collection)
                session.flush()  # Added: Flush after each collection
                session.expire_all()  # Added: Expire after each collection

                # Log with additional context about the ObjectType relationship
                log_message = f"Created collection {type_name}"
                if logical_name:
                    log_message += f" linked to object type {logical_name}"
                else:
                    log_message += " with no ObjectType relationship"
                logger.debug(log_message)

            except Exception as e:
                logger.error(f"Error creating collection {type_name}: {str(e)}")
                raise

        # Ensure collections are fully committed
        session.flush()

        logger.debug(f"Created {len(collections)} collections")

        # 4. Process field mappings
        field_mappings = connector._process_field_mappings(json_data, session)
        try:
            connector._create_field_maps(field_mappings, session)
        except Exception as e:
            logger.error(f"Error creating field mappings: {str(e)}")
            raise
        session.flush()


        # 5. Process functions
        if "functions" in schema_data:
            logger.debug("Processing functions")
            for func_data in schema_data["functions"]:
                if isinstance(func_data, dict):
                    try:
                        Function.from_json(func_data, connector, session)
                    except Exception as e:
                        logger.error(f"Error processing function {func_data.get('name')}: {str(e)}")
                        raise
        session.flush()


        # 6. Process procedures last
        if "procedures" in schema_data:
            logger.debug("Processing procedures")
            for proc_data in schema_data["procedures"]:
                if isinstance(proc_data, dict):
                    try:
                        Procedure.from_json(proc_data, connector, session)
                    except Exception as e:
                        logger.error(f"Error processing procedure {proc_data.get('name')}: {str(e)}")
                        raise

        return connector

    def to_json(self) -> Dict[str, Any]:
        """Serialize the DataConnector and its related entities to JSON."""
        # Convert models to JSON representation
        json_data = self._convert_models_to_json()

        # Create base connector structure
        connector_dict: Dict[str, Any] = {
            "kind": "DataConnectorLink",
            "version": "v1",
            "definition": {
                "name": self.name,
                "url": {
                    "readWriteUrls": {
                        "read": {"value": self.read_url},
                        "write": {"value": self.write_url}
                    }
                },
                "schema": {
                    "version": self.schema_version,
                    "capabilities": self.capabilities.to_json() if self.capabilities else {},
                    "schema": {
                        "collections": [],
                        "functions": [],
                        "procedures": [],
                        "scalar_types": {},
                        "object_types": {}
                    }
                }
            }
        }

        # Add converted model data
        connector_dict["definition"].update(json_data)

        schema_section = connector_dict["definition"]["schema"]["schema"]

        # Add scalar types
        for scalar_type in self.scalar_types:
            scalar_dict = {
                "aggregate_functions": {},
                "comparison_operators": {}
            }

            if scalar_type.representation_name:
                scalar_dict["representation"] = scalar_type.representation.to_json()

            # Add aggregate functions
            for func in scalar_type.aggregate_functions:
                scalar_dict["aggregate_functions"][func.function_name] = func.to_json()

            # Filter comparison operators by scalar type name
            scalar_ops = [op for op in self.comparison_operators
                          if op.scalar_type_name == scalar_type.name and
                          op.scalar_type_connector_name == scalar_type.connector_name and
                          op.scalar_type_subgraph_name == scalar_type.subgraph_name]

            # Add filtered comparison operators
            for op in scalar_ops:
                scalar_dict["comparison_operators"][op.name] = op.to_json()

            schema_section["scalar_types"][scalar_type.name] = scalar_dict

        # Add collections with proper structure
        for collection in self.collections:
            if collection.object_type_name:  # Only include collections with an associated object type
                collection_dict = {
                    "arguments": {},
                    "foreign_keys": self._get_collection_foreign_keys(collection),
                    "name": collection.name,
                    "type": collection.name,
                    "uniqueness_constraints": self._get_collection_constraints(collection)
                }
                schema_section["collections"].append(collection_dict)

        # Add object types with proper field structure
        for obj_type in self.collections:
            fields_dict = {}
            for field in obj_type.fields:
                field_type = {
                    "type": field.type_definition.to_json()
                }
                if field.description:
                    field_type["description"] = field.description
                fields_dict[field.physical_field_name] = field_type

            schema_section["object_types"][obj_type.name] = {
                "fields": fields_dict
            }
            if obj_type.description is not None:
                schema_section["object_types"][obj_type.name]["description"] = obj_type.description

        # Add functions and procedures
        schema_section["functions"] = [func.to_json() for func in self.functions]
        schema_section["procedures"] = [proc.to_json() for proc in self.procedures]

        return connector_dict

    @staticmethod
    def _get_collection_foreign_keys(collection) -> Dict[str, Any]:
        """
        Extract foreign key relationships for a collection.

        Args:
            collection: Collection object to extract foreign keys from

        Returns:
            Dictionary containing foreign key definitions
        """
        return {fk.fk_name: fk.to_json() for fk in collection.foreign_keys}

    @staticmethod
    def _get_collection_constraints(collection) -> Dict[str, Any]:
        """
        Extract uniqueness constraints for a collection.

        Args:
            collection: Collection object to extract constraints from

        Returns:
            Dictionary containing uniqueness constraint definitions
        """
        return {
            constraint.constraint_name: {
                "unique_columns": [column.field_name for column in constraint.columns]
            }
            for constraint in collection.uniqueness_constraints
        }
