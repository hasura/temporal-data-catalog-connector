from typing import overload, Optional, Union, TYPE_CHECKING

from rdflib import Graph, URIRef, RDF, Literal
from sqlalchemy.orm import Session

from .base_rdf_mixin import BaseRDFMixin
from .namespace import bind_namespaces
from .rdf_translator import T, RDFTranslator

if TYPE_CHECKING:
    from ... import ObjectType
    from ...object_type.field import ObjectField
    from ...relationship import Relationship

logger = __import__("logging").getLogger(__name__)


class ModelRDFMixin(BaseRDFMixin):
    """Mixin class for handling model-level RDF hasura_metadata_manager."""

    @classmethod
    def _to_pascal_case(cls, name: str) -> str:
        """Convert a string to PascalCase"""
        words = ''.join(c if c.isalnum() else ' ' for c in name).split()
        return ''.join(word.capitalize() for word in words)

    @classmethod
    def _to_upper_snake_case(cls, name: str) -> str:
        """Convert a string to UPPER_SNAKE_CASE"""
        import re
        # Insert underscore before uppercase letters, then convert to uppercase
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()

    @classmethod
    def generate_model_metadata_graph(cls, session: Session) -> Graph:
        """Generate RDF graph representing the model structure from metadata tables"""
        logger.debug("Generating model metadata graph")
        graph = Graph()
        bind_namespaces(graph)

        # Get all current object types, fields and relationships
        object_types = session.query(ObjectType).filter(
            ObjectType.t_is_current == True,
            ObjectType.t_is_deleted == False
        ).all()

        object_fields = session.query(ObjectField).filter(
            ObjectField.t_is_current == True,
            ObjectField.t_is_deleted == False
        ).all()

        relationships = session.query(Relationship).filter(
            Relationship.t_is_current == True,
            Relationship.t_is_deleted == False
        ).all()

        # Create nodes for each object type with its fields
        for obj_type in object_types:
            # Create node with labels
            type_uri = URIRef(obj_type.name)
            graph.add((type_uri, RDF.type, URIRef(obj_type.subgraph_name)))
            graph.add((type_uri, RDF.type, URIRef(cls._to_pascal_case(obj_type.name))))

            # Add fields as properties
            fields = [f for f in object_fields if f.object_type_name == obj_type.name]
            for field in fields:
                graph.add((type_uri, URIRef(field.logical_field_name),
                           Literal(field.scalar_type_name)))

        # Add relationships
        for rel in relationships:
            source_uri = URIRef(rel.source_type_name)
            target_uri = URIRef(rel.target_type_name)
            rel_name = cls._to_upper_snake_case(rel.name)
            graph.add((source_uri, URIRef(rel_name), target_uri))

        logger.debug("Completed model metadata graph generation")
        return graph

    @classmethod
    @overload
    def translate_to_model_metadata(cls, session: Session) -> Graph:
        ...

    @classmethod
    @overload
    def translate_to_model_metadata(cls, session: Session, translator: RDFTranslator[T]) -> T:
        ...

    @classmethod
    def translate_to_model_metadata(
            cls,
            session: Session,
            translator: Optional[RDFTranslator[T]] = None
    ) -> Union[Graph, T]:
        """Generate and optionally translate model hasura_metadata_manager"""
        cls._ensure_cache_configured()

        if not cls._cache_manager:
            logger.warning("Cache not configured, proceeding without caching")
            graph = cls.generate_model_metadata_graph(session=session)
        else:
            graph = cls._cache_manager.get_model_metadata(
                cls=cls,
                session=session,
                generator_func=cls.generate_model_metadata_graph
            )

        return translator.translate(graph) if translator else graph

