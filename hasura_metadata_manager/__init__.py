# In src/hasura_metadata_manager/__init__.py
import logging

from sqlalchemy import MetaData, ForeignKeyConstraint
from sqlalchemy.orm import configure_mappers
from sqlalchemy.sql.ddl import AddConstraint

from .relationship.relationship_base import RelationshipType

# Logging setup for debugging and tracking initialization steps
logger = logging.getLogger(__name__)

# Independent model imports: Import models with minimal dependencies first
# (This ensures that models which don't depend on others in the hierarchy are imported beforehand)
from .data_connector import DataConnector
from .object_type import ObjectType
from .aggregate_expression import AggregateExpression
from .boolean_expression_type import BooleanExpressionType
from .graphql_config import GraphQLConfig
from .auth_config import AuthConfig
from .model_permission import ModelPermission
from .role import Role
from .supergraph import Supergraph
from .type_permission import TypePermission
from .command_permissions import CommandPermissions
from .command import Command

# Schema and Field dependencies
# Ensure ScalarType is imported first since other models depend on it
from .data_connector.schema.scalar_type.scalar_type import ScalarType
from .data_connector_scalar_representation import DataConnectorScalarRepresentation
from .data_connector.schema.collection.collection import Collection
from .data_connector.field_map.field_map import FieldMap
from .data_connector.schema.collection.field.collection_field import CollectionField

# Filter dependencies
# Ensure proper order: Import FilterOperand first since FilterOperation depends on it
from .model_permission.filter.filter_operand import FilterOperand
from .model_permission.filter.filter_operation import FilterOperation

# Subgraph and Supergraph imports
from .subgraph import Subgraph  # Subgraph must come before Supergraph

# Model imports directly related to your issue
from .relationship import RelationshipAggregate, \
    TargetModel  # Import TargetModel after dependencies like RelationshipAggregate


# Helper function: Log and validate registered tables in the hasura_metadata_manager
def log_registered_tables():
    from .base import Base  # Base is shared across all models
    logger.info("Registered tables:")
    for table_name in Base.metadata.tables.keys():
        logger.info(f"  {table_name}")  # Log each registered table name


# Trigger SQLAlchemy to configure all mappers (ensures relationships between models are fully resolved)
try:
    configure_mappers()
    logger.info("Successfully configured SQLAlchemy mappers.")
except Exception as e:
    logger.error(f"Error during SQLAlchemy mapper configuration: {e}")
    raise

# Log registered tables to confirm mappings
log_registered_tables()


def create_viewonly_fk_constraints(metadata: MetaData, engine):
    """
    Dynamically add view-only FK constraints to tables in a database-agnostic way.
    """
    for table in metadata.tables.values():
        for fk in table.foreign_keys:
            # Check if the FK should be created based on the `info` marker in relationships
            if fk.info.get("create_fk_later", False):
                print(f"Creating FK constraint: {fk.parent.table.name}.{fk.parent.name} "
                      f"-> {fk.column.table.name}.{fk.column.name}")

                # Dynamically create and add a ForeignKeyConstraint
                constraint = ForeignKeyConstraint(
                    columns=[fk.parent],
                    refcolumns=[fk.target_fullname]
                )
                with engine.begin() as conn:
                    conn.execute(AddConstraint(constraint))

                # Add the constraint to the table for ORM purposes
                table.append_constraint(constraint)


from .load import init_with_session
from .export_rdf import export_rdf
from .export_model_rdf import export_model_rdf
from .sync_model_to_neo4j import sync_model_to_neo4j

__all__ = [
    'init_with_session',
    'ModelPermission',
    'ObjectType',
    'Supergraph',
    'Subgraph',
    'AuthConfig',
    'AggregateExpression',
    'BooleanExpressionType',
    'DataConnector',
    'DataConnectorScalarRepresentation',
    'FilterOperand',
    'RelationshipType',
    'RelationshipAggregate',
    'ScalarType',
    'GraphQLConfig',
    'FieldMap',
    'CollectionField',
    'FilterOperation',
    'Role',
    'TypePermission',
    'Collection',
    'export_rdf',
    'export_model_rdf',
    'sync_model_to_neo4j'
]
