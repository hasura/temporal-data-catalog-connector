from typing import List, Type, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session
import os

from .subgraph_base import Subgraph as BaseSubgraph
from ..compatibility_config import CompatibilityConfig
from ..graphql_config import GraphQLConfig
from ..lifecycle_plugin_hook import LifecyclePluginHook
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..object_type import ObjectType
from ..relationship import Relationship

if TYPE_CHECKING:
    from ..boolean_expression_type import BooleanExpressionType
    from ..aggregate_expression import AggregateExpression
    from ..data_connector import DataConnector
    from ..type_permission import TypePermission
    from ..model_permission import ModelPermission
    from ..data_connector.schema.scalar_type import ScalarType
    from ..data_connector_scalar_representation.data_connector_scalar_representation import \
        DataConnectorScalarRepresentation
    from ..auth_config import AuthConfig
    from ..supergraph import SubgraphSupergraphMap
    from ..supergraph import Supergraph
    from ..model import Model
    from ..role import Role


class Subgraph(BaseSubgraph):
    """
    Subgraph implementation class that includes relationships and methods.
    """
    __tablename__ = "subgraph"

    # Core relationships with explicit joins and foreign() annotation
    relationships: Mapped[List["Relationship"]] = TemporalRelationship(
        "Relationship",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == Relationship.subgraph_name)",
        info={'skip_constraint': True}
    )
    data_connectors: Mapped[List["DataConnector"]] = TemporalRelationship(
        "DataConnector",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == DataConnector.subgraph_name)",
        info={'skip_constraint': True}
    )
    scalar_types: Mapped[List["ScalarType"]] = TemporalRelationship(
        "ScalarType",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == ScalarType.subgraph_name)",
        info={'skip_constraint': True}
    )

    # Additional core relationships with explicit joins
    models: Mapped[List["Model"]] = TemporalRelationship(
        "Model",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name)== Model.subgraph_name)",
        info={'skip_constraint': True}
    )

    type_permissions: Mapped[List["TypePermission"]] = TemporalRelationship(
        "TypePermission",
        uselist=True,
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == TypePermission.subgraph_name)",
        info={'skip_constraint': True}
    )

    data_connector_scalar_representations: Mapped[List["DataConnectorScalarRepresentation"]] = TemporalRelationship(
        "DataConnectorScalarRepresentation",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == DataConnectorScalarRepresentation.subgraph_name)",
        info={'skip_constraint': True}
    )

    compatibility_config: Mapped["CompatibilityConfig"] = TemporalRelationship(
        "CompatibilityConfig",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == CompatibilityConfig.subgraph_name)",
        uselist=False
    )

    object_types: Mapped[List["ObjectType"]] = TemporalRelationship(
        "ObjectType",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == ObjectType.subgraph_name)",
        info={'skip_constraint': True}
    )

    lifecycle_plugin_hooks: Mapped[List["LifecyclePluginHook"]] = TemporalRelationship(
        "LifecyclePluginHook",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == LifecyclePluginHook.subgraph_name)",
        info={'skip_constraint': True}
    )

    supergraph_maps: Mapped[List["SubgraphSupergraphMap"]] = TemporalRelationship(
        "SubgraphSupergraphMap",
        viewonly=True,
        primaryjoin="and_(foreign(Subgraph.name) == SubgraphSupergraphMap.subgraph_name)",
        uselist=True,
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["Subgraph"], json_data: Dict[str, Any], supergraph: "Supergraph",
                  session: Session) -> "Subgraph":
        """
        Create a Subgraph from JSON data.

        Args:
            json_data: Dictionary containing subgraph configuration
            supergraph: Parent Supergraph instance
            session: SQLAlchemy session

        Returns:
            Created Subgraph instance
        """
        # Import ScalarType here to avoid circular import
        from ..data_connector.schema.scalar_type import ScalarType
        from ..data_connector import DataConnector
        from ..aggregate_expression import AggregateExpression
        from ..supergraph import SubgraphSupergraphMap
        from ..model import Model
        from ..role import Role

        subgraph = cls(
            name=json_data["name"],
            description=json_data.get("description")
        )
        session.add(subgraph)
        session.flush()

        # Create the mapping in the SubgraphSupergraphMap table
        mapping = SubgraphSupergraphMap(
            subgraph_name=subgraph.name,
            supergraph_name=supergraph.name
        )
        session.add(mapping)
        session.flush()  # Ensure the mapping is flushed
        # session.commit()

        ordered_kinds = [
            # Logical Layer
            "CompatibilityConfig",
            "LifecyclePluginHook",
            "ScalarType",
            "ObjectType",
            "Model",
            "AggregateExpression",  # Depends on ScalarType and Model
            "Relationship",
            "BooleanExpressionType.scalar",  # Process scalar-based first
            "BooleanExpressionType.object",
            "TypePermissions",
            "ModelPermissions",
            "AuthConfig",
            "GraphqlConfig",  # Depends on the availability of other object types
            "DataConnectorScalarRepresentation",
            "Command",
            "CommandPermissions",

            # Physical Layer
            "DataConnectorLink",  # Bridge between logical and physical
        ]

        from ..auth_config import AuthConfig
        excluded_objects = os.getenv('EXCLUDED_OBJECTS', '').split(',') if os.getenv('EXCLUDED_OBJECTS') else []

        # Process objects in specified order
        for kind in ordered_kinds:
            if "objects" in json_data:
                for obj in [obj for obj in json_data["objects"] if obj.get("kind") == kind.split('.')[0] and obj.get(
                        "definition", {}).get("name") not in excluded_objects]:
                    try:
                        if kind == "DataConnectorLink":
                            dc = DataConnector.from_json(obj, subgraph, session)
                            if dc:
                                session.flush()
                                # session.commit()
                        elif kind == "ObjectType":
                            ot = ObjectType.from_json(obj, subgraph, session)
                            if ot:
                                session.flush()
                                # session.commit()
                        elif kind == "ScalarType":
                            st = ScalarType.from_json(obj, subgraph, session)
                            if st:
                                session.flush()
                                # session.commit()
                        elif kind == "GraphqlConfig":
                            gc = GraphQLConfig.from_json(obj, subgraph, session)
                            if gc:
                                session.flush()
                        elif kind == "TypePermissions":
                            role = Role.from_json(obj, subgraph, supergraph, session)
                            if role:
                                session.flush()
                                # session.commit()
                        elif kind == "BooleanExpressionType.scalar":
                            if obj.get("kind") == "BooleanExpressionType":
                                from ..boolean_expression_type import boolean_expression_type as bet_module
                                def_data = obj.get("definition", {})
                                operand_data = def_data.get("operand", {})
                                if "scalar" in operand_data:
                                    bet = bet_module.BooleanExpressionType.from_json(json_data=obj, subgraph=subgraph,
                                                                                     session=session)
                                    if bet:
                                        session.flush()
                                        # session.commit()
                        elif kind == "BooleanExpressionType.object":
                            if obj.get("kind") == "BooleanExpressionType":
                                from ..boolean_expression_type import boolean_expression_type as bet_module
                                def_data = obj.get("definition", {})
                                operand_data = def_data.get("operand", {})
                                if "object" in operand_data:
                                    bet = bet_module.BooleanExpressionType.from_json(json_data=obj, subgraph=subgraph,
                                                                                     session=session)
                                    if bet:
                                        session.flush()
                                        # session.commit()
                        elif kind == "AggregateExpression":
                            aq = AggregateExpression.from_json(obj, subgraph, session)
                            if aq:
                                session.flush()
                                # session.commit()
                        elif kind == "Model":
                            m = Model.from_json(obj, subgraph, session)
                            if m:
                                session.flush()
                                # session.commit()
                        elif kind == "AuthConfig":
                            ac = AuthConfig.from_json(obj, subgraph, session)
                            if ac:
                                session.flush()
                                # session.commit()
                        elif kind == "CompatibilityConfig":
                            cc = CompatibilityConfig.from_json(obj, subgraph, session)
                            if cc:
                                session.flush()
                                # session.commit()
                        elif kind == "LifecyclePluginHook":
                            cc = LifecyclePluginHook.from_json(obj, subgraph, session)
                            if cc:
                                session.flush()
                                # session.commit()
                        elif kind == "Relationship":
                            r = Relationship.from_json(obj, subgraph, session)
                            if r:
                                session.flush()
                                # session.commit()
                        elif kind == "DataConnectorScalarRepresentation":
                            from ..data_connector_scalar_representation import \
                                data_connector_scalar_representation as dcsr_module
                            dcsr = dcsr_module.DataConnectorScalarRepresentation.from_json(obj, subgraph, session)
                            if dcsr:
                                session.flush()
                                # session.commit()
                        elif kind == "ModelPermissions":
                            from ..model_permission import model_permission as mp_module
                            mp = mp_module.ModelPermission.from_json(obj, subgraph, session)
                            if mp:
                                session.flush()
                        elif kind == "CommandPermissions":
                            from ..command_permissions import command_permissions as cp_module
                            cp = cp_module.CommandPermissions.from_json(obj, subgraph.name, session)
                            if cp:
                                session.flush()
                        elif kind == "Command":
                            from ..command import command as c_module
                            c = c_module.Command.from_json(obj, subgraph.name, session)
                            if c:
                                session.flush()
                                # session.commit()
                    except Exception as e:
                        # Log error but continue processing other objects
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Error processing {kind} object: {str(e)}")
                        raise

        return subgraph

    def to_dict(self):
        """
        Convert the Subgraph to a dictionary representation.

        Returns:
            dict: A dictionary with the Subgraph's basic attributes
        """
        return {key: value for key, value in {
            'name': self.name,
            'description': self.description
        }.items() if value is not None}

    def query_subgraph_objects(self, model_class, session):
        """
        Query objects of a specific model class for this subgraph using a provided session.

        Args:
            model_class (Type): The SQLAlchemy model class to query
            session (Session): SQLAlchemy session to use for querying

        Returns:
            List: List of objects belonging to this subgraph
        """
        # Check if the model has a subgraph_name attribute
        if hasattr(model_class, 'subgraph_name'):
            # Use the provided session to query objects
            return session.query(model_class).filter_by(subgraph_name=self.name).all()

        # If no subgraph_name, return an empty list
        return []

    def to_json(self, session: Session):
        """
        Prepare the Subgraph for JSON serialization in metadata.json format.

        Returns:
            dict: A dictionary representing the Subgraph with 'kind' and other hasura_metadata_manager
        """
        # Start with the basic dictionary from to_dict()
        json_dict = self.to_dict()

        from ..data_connector.schema.scalar_type import ScalarType
        from ..aggregate_expression import AggregateExpression
        from ..boolean_expression_type import BooleanExpressionType
        from ..data_connector import DataConnector
        from ..type_permission import TypePermission
        from ..model_permission import ModelPermission
        from ..auth_config import AuthConfig
        from ..model import Model
        from ..data_connector_scalar_representation.data_connector_scalar_representation import \
            DataConnectorScalarRepresentation

        # Configuration and hasura_metadata_manager objects to collect
        object_types = [
            (LifecyclePluginHook, 'LifecyclePluginHook'),
            (AuthConfig, 'AuthConfig'),
            (CompatibilityConfig, 'CompatibilityConfig'),
            (GraphQLConfig, 'GraphqlConfig'),
            (ScalarType, 'ScalarType'),
            (ObjectType, 'ObjectType'),
            (Model, 'Model'),
            (AggregateExpression, 'AggregateExpression'),
            (BooleanExpressionType, 'BooleanExpressionType'),
            (Relationship, 'Relationship'),
            (TypePermission, 'TypePermissions'),
            (ModelPermission, 'ModelPermissions'),
            (DataConnectorScalarRepresentation, 'DataConnectorScalarRepresentation'),
            (DataConnector, 'DataConnectorLink'),
        ]

        # Collect objects for this specific subgraph
        objects = []
        for model, kind in object_types:

            subgraph_objects = self.query_subgraph_objects(model, session)

            # Convert each object to JSON and add kind
            for obj in subgraph_objects:
                obj_json = obj.to_json()
                if obj_json:
                    objects.append(obj_json)

        # Add objects to the dictionary if any exist
        if objects:
            json_dict['objects'] = objects

        return json_dict
