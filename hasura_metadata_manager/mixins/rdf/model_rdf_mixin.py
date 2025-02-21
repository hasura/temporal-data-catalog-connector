from typing import overload, Optional, Union, cast, List

from rdflib import Graph, URIRef, RDF, Literal, RDFS
from sqlalchemy.orm import Session

from . import NS_HASURA_REL
from .base_rdf_mixin import BaseRDFMixin
from .namespace import bind_namespaces, NS_HASURA_MODEL, NS_HASURA_SUBGRAPH, NS_HASURA_PROP
from .rdf_translator import T, RDFTranslator

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

        from ... import ObjectType
        from ...object_type.field import ObjectField
        from ...relationship import Relationship

        logger.debug("Generating model metadata graph")
        graph = Graph()
        bind_namespaces(graph)

        # Get all current object types, fields and relationships
        object_types = cast(List[ObjectType],session.query(ObjectType).filter(
            ObjectType.t_is_current,
            ~ObjectType.t_is_deleted
        ).all())

        object_fields = cast(List[ObjectField],session.query(ObjectField).filter(
            ObjectField.t_is_current,
            ~ObjectField.t_is_deleted
        ).all())

        relationships = cast(List[Relationship],session.query(Relationship).filter(
            Relationship.t_is_current,
            ~Relationship.t_is_deleted
        ).all())

        # Create nodes for each object type with its fields
        for obj_type in object_types:
            # Create node with labels
            graph.add((
                NS_HASURA_MODEL[obj_type.name],
                NS_HASURA_REL["BELONGS_TO"],
                NS_HASURA_SUBGRAPH[obj_type.subgraph_name]
            ))
            graph.add((NS_HASURA_MODEL[obj_type.name], RDF.type, NS_HASURA_MODEL.Model))
            graph.add((NS_HASURA_SUBGRAPH[obj_type.subgraph_name], RDF.type, NS_HASURA_SUBGRAPH.Subgraph))
            graph.add((NS_HASURA_MODEL[obj_type.name], RDFS.label, Literal(obj_type.name)))
            graph.add((NS_HASURA_SUBGRAPH[obj_type.subgraph_name], RDFS.label, Literal(obj_type.subgraph_name)))

            # Add fields as properties
            fields = [f for f in object_fields if f.object_type_name == obj_type.name]
            for field in fields:
                graph.add((NS_HASURA_MODEL[obj_type.name], NS_HASURA_REL["HAS_PROPERTY"],
                           NS_HASURA_PROP[field.name]))
                graph.add((NS_HASURA_PROP[field.name], RDFS.label, Literal(field.name)))
                graph.add((NS_HASURA_PROP[field.name], RDF.type, NS_HASURA_PROP.Property))


        # Add relationships
        for rel in relationships:
            source_uri = NS_HASURA_MODEL[rel.source_type_name]
            target_uri = NS_HASURA_MODEL[rel.target_type_name]
            rel_name = "HAS_" + cls._to_upper_snake_case(rel.name)
            graph.add((source_uri, NS_HASURA_REL[rel_name], target_uri))

        # assert len(graph) > 0, "Generated model RDF graph is empty"
        logger.debug(f"Completed model metadata graph generation: {len(graph)}")
        for subj, pred, obj in graph.triples((None, None, None)):
            logger.debug(f"Subject: {subj}, Predicate: {pred}, Object: {obj}")
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

