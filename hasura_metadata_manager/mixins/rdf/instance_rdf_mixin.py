import urllib.parse
from inspect import getmembers
from typing import List, Optional, overload, Union, cast

from rdflib import URIRef, Graph, RDF
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from . import NS_HASURA, NS_HASURA_PROP, NS_HASURA_REL
from .base_rdf_mixin import BaseRDFMixin
from .namespace import bind_namespaces

logger = __import__("logging").getLogger(__name__)
from .rdf_translator import T
from .rdf_translator import RDFTranslator


class InstanceRDFMixin(BaseRDFMixin):
    """Mixin class for handling instance-level RDF hasura_metadata_manager."""

    @classmethod
    def get_rdf_properties(cls) -> List[str]:
        """Get properties that should be included in the instance RDF graph"""
        mapper = inspect(cls)
        # Get physical columns
        db_properties = [c.key for c in mapper.column_attrs]

        # Get Python @property decorators
        property_attributes = [name for name, attr in getmembers(cls, lambda x: isinstance(x, property))]

        properties = db_properties + property_attributes
        logger.debug(f"Retrieved {len(properties)} RDF properties for class {cls.__name__}: {properties}")
        return properties

    def _get_subject_uri(self) -> URIRef:
        """Get the subject URI for this instance"""
        primary_keys = inspect(self.__class__).primary_key
        pk_values = "_".join(
            urllib.parse.quote(str(getattr(self, key.name)))
            for key in primary_keys
        )
        uri = URIRef(NS_HASURA[f"{self.__class__.__name__}#{pk_values}"])
        logger.debug(f"Generated subject URI: {uri}")
        return uri

    @staticmethod
    def _get_related_uri(related_object) -> URIRef:
        """Get the RDF URI of a related object for instance relationships"""
        logger.debug(f"Generating URI for related object of type: {related_object.__class__.__name__}")
        primary_keys = inspect(related_object.__class__).primary_key
        pk_values = "_".join(
            urllib.parse.quote(str(getattr(related_object, key.name)))
            for key in primary_keys
        )
        uri = URIRef(NS_HASURA[f"{related_object.__class__.__name__}#{pk_values}"])
        logger.debug(f"Generated related URI: {uri}")
        return uri

    def _add_property_triples(self, graph: Graph, subject_uri: URIRef) -> str:
        """Add property triples to the graph for instance hasura_metadata_manager"""
        logger.debug(f"Adding property triples for subject: {subject_uri}")
        properties_added = 0
        query_params = []

        for prop in self.get_rdf_properties():
            value = getattr(self, prop)
            if value is not None:
                predicate_uri = NS_HASURA_PROP[prop]
                literal_value = self._format_literal(value)
                graph.add((subject_uri, predicate_uri, literal_value))
                properties_added += 1
                logger.debug(f"Added property triple - {prop}: {literal_value}")

                # Add to query params
                encoded_value = urllib.parse.quote(str(value))
                query_params.append(f"{prop}={encoded_value}")

        logger.debug(f"Added {properties_added} property triples to graph")
        return "&".join(query_params)

    def _add_relationship_triples(self, graph: Graph, subject_uri: URIRef) -> None:
        """Add relationship triples to the graph for instance hasura_metadata_manager"""
        logger.debug(f"Adding relationship triples for subject: {subject_uri}")
        relationships_added = 0

        for relationship_name, relationship in inspect(self.__class__).relationships.items():
            related_object = getattr(self, relationship_name)
            if related_object is not None:
                if relationship.uselist:
                    logger.debug(f"Processing list relationship: {relationship_name}")
                    predicate_uri = NS_HASURA_REL["HAS_MANY"]
                    for obj in related_object:
                        related_uri = self._get_related_uri(obj)
                        graph.add((subject_uri, predicate_uri, related_uri))
                        relationships_added += 1
                else:
                    logger.debug(f"Processing single relationship: {relationship_name}")
                    predicate_uri = NS_HASURA_REL["HAS_ONE"]
                    related_uri = self._get_related_uri(related_object)
                    graph.add((subject_uri, predicate_uri, related_uri))
                    relationships_added += 1

        logger.debug(f"Added {relationships_added} relationship triples to graph")

    def _generate_instance_rdf(self, session: Session) -> Graph:
        """Generate instance-specific RDF hasura_metadata_manager"""
        graph = Graph()
        bind_namespaces(graph)

        subject_uri = self._get_subject_uri()
        graph.add((subject_uri, RDF.type, self.get_rdf_type()))

        self._add_property_triples(graph, subject_uri)
        self._add_relationship_triples(graph, subject_uri)

        return graph

    def to_rdf_graph(self, session: Session, _graph: Optional[Graph] = None) -> Graph:
        """Convert a specific instance into an RDF graph with caching"""
        self.__class__._ensure_cache_configured()

        if not self._cache_manager:
            logger.warning("Cache not configured, proceeding without caching")
            return self._generate_instance_rdf(session)

        if not self._cache_manager.is_fresh():
            logger.info("Cache is stale, clearing all caches")
            self.clear_caches()

        return self._cache_manager.get_instance_metadata(
            instance=self,
            session=session,
            generator_func=self._generate_instance_rdf
        )

    @classmethod
    def generate_instance_metadata_graph(cls, session: Session) -> Graph:
        """Generate RDF graph representing hasura_metadata_manager for specific supergraph instances"""
        logger.debug(f"Generating instance hasura_metadata_manager RDF graph for {cls.__name__}")
        all_graphs = Graph()
        bind_namespaces(all_graphs)
        instance_count = 0

        for instance in cast(List[InstanceRDFMixin], session.query(cls).all()):
            instance_graph = instance.to_rdf_graph(session=session)
            all_graphs += instance_graph
            instance_count += 1
            if instance_count % 100 == 0:
                logger.debug(f"Processed {instance_count} instance hasura_metadata_manager entries")

        logger.debug(f"Completed instance hasura_metadata_manager graph generation. Total instances: {instance_count}")
        return all_graphs

    @classmethod
    @overload
    def translate_to_instance_metadata(cls, session: Session) -> Graph:
        ...

    @classmethod
    @overload
    def translate_to_instance_metadata(cls, session: Session, translator: RDFTranslator[T]) -> T:
        ...

    @classmethod
    def translate_to_instance_metadata(
            cls,
            session: Session,
            translator: Optional[RDFTranslator[T]] = None
    ) -> Union[Graph, T]:
        """Generate and optionally translate instance hasura_metadata_manager"""
        cls._ensure_cache_configured()

        if not cls._cache_manager:
            logger.warning("Cache not configured, proceeding without caching")
            graph = cls.generate_instance_metadata_graph(session)
        else:
            graph = cls._cache_manager.get_bulk_instance_metadata(
                cls=cls,
                session=session,
                generator_func=lambda: cls.generate_instance_metadata_graph(session)
            )

        return translator.translate(graph) if translator else graph
