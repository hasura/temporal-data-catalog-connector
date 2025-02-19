from typing import overload, Optional, Union

from rdflib import Graph, URIRef, RDF, Literal
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .base_rdf_mixin import BaseRDFMixin
from .namespace import NS_HASURA_MODEL, bind_namespaces
from .rdf_translator import T, RDFTranslator

logger = __import__("logging").getLogger(__name__)


class ModelRDFMixin(BaseRDFMixin):
    """Mixin class for handling model-level RDF hasura_metadata_manager."""

    @classmethod
    def generate_model_metadata_graph(cls, session: Session) -> Graph:
        """Generate RDF graph representing the supergraph model structure"""
        logger.debug(f"Generating model hasura_metadata_manager graph for {cls.__name__}")
        graph = Graph()
        bind_namespaces(graph)

        # Add model-level type definition
        model_uri = URIRef(NS_HASURA_MODEL[cls.__name__])
        graph.add((model_uri, RDF.type, NS_HASURA_MODEL.Entity))

        # Add property definitions
        mapper = inspect(cls)
        for column in mapper.columns:
            prop_uri = URIRef(NS_HASURA_MODEL[f"{cls.__name__}_{column.name}"])
            graph.add((prop_uri, RDF.type, NS_HASURA_MODEL.Property))
            graph.add((prop_uri, NS_HASURA_MODEL.belongsTo, model_uri))
            graph.add((prop_uri, NS_HASURA_MODEL.dataType, Literal(str(column.type))))

            # Add constraints
            if not column.nullable:
                graph.add((prop_uri, NS_HASURA_MODEL.required, Literal(True)))
            if column.primary_key:
                graph.add((prop_uri, NS_HASURA_MODEL.primaryKey, Literal(True)))

        # Add relationship definitions
        for relationship in mapper.relationships:
            rel_uri = URIRef(NS_HASURA_MODEL[f"{cls.__name__}_{relationship.key}"])
            graph.add((rel_uri, RDF.type, NS_HASURA_MODEL.Relationship))
            graph.add((rel_uri, NS_HASURA_MODEL.source, model_uri))
            graph.add((rel_uri, NS_HASURA_MODEL.target,
                       URIRef(NS_HASURA_MODEL[relationship.mapper.class_.__name__])))
            graph.add((rel_uri, NS_HASURA_MODEL.cardinality,
                       Literal("many" if relationship.uselist else "one")))

        logger.debug(f"Completed model hasura_metadata_manager graph generation for {cls.__name__}")
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
