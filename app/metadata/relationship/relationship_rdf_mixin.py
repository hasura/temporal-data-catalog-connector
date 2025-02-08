import logging
from typing import TYPE_CHECKING

from rdflib import URIRef, Graph
from sqlalchemy.orm import Session

from ..mixins.rdf import NS_HASURA, NS_HASURA_OBJ_REL, RDFGeneratorMixin
from ..mixins.rdf.namespace import bind_namespaces

if TYPE_CHECKING:
    from .. import RelationshipAggregate
    from ..relationship import Relationship
    from .relationship_field_mapping import RelationshipFieldMapping

logger = logging.getLogger(__name__)


class RelationshipRDFMixin(RDFGeneratorMixin):
    """RDF generation mixin specifically for relationship instance metadata"""

    def _generate_instance_rdf(self, session: Session) -> Graph:
        """Generate instance-specific RDF metadata for relationships"""
        logger.debug("Starting instance metadata generation for %s", self.__class__.__name__)
        graph = Graph()
        bind_namespaces(graph)

        from .. import RelationshipAggregate
        from ..relationship import Relationship
        from .relationship_field_mapping import RelationshipFieldMapping

        if isinstance(self, Relationship):
            logger.debug("Generating instance metadata for Relationship: subgraph=%s, name=%s",
                         self.subgraph_name, self.name)

            # Create direct relationship URI and add type info
            rel_uri = URIRef(NS_HASURA_OBJ_REL["HAS_" + self.relationship_type.upper()])
            logger.debug("Created relationship URI: %s", rel_uri)

            # Create direct connection between source and target types
            source_type = URIRef(NS_HASURA[f"ObjectType#{self.subgraph_name}_{self.source_type_name}"])
            target_type = URIRef(NS_HASURA[f"ObjectType#{self.subgraph_name}_{self.target_type_name}"])
            logger.debug("Adding triple: %s -> %s -> %s", source_type, rel_uri, target_type)
            graph.add((source_type, rel_uri, target_type))

            # Add instance metadata triples
            self._add_property_triples(graph, rel_uri)
            self._add_relationship_triples(graph, rel_uri)

        elif isinstance(self, RelationshipFieldMapping):
            logger.debug("Generating instance metadata for FieldMapping: source=%s, target=%s",
                         self.source_field, self.target_field)

            field_uri = URIRef(NS_HASURA[f"FieldMap#{self.subgraph_name}_{self.source_field}_{self.target_field}"])
            logger.debug("Created field mapping URI: %s", field_uri)

            # Add instance metadata triples
            self._add_property_triples(graph, field_uri)

            # Add specific connection to parent relationship if it exists
            if self.parent_relationship:
                parent_uri = URIRef(NS_HASURA_OBJ_REL[self.parent_relationship.relationship_type])
                logger.debug("Adding parent relationship connection: %s -> %s",
                             field_uri, parent_uri)
                graph.add((field_uri, URIRef(NS_HASURA["#match_fields_for"]), parent_uri))
            else:
                logger.debug("No parent relationship found for field mapping")

        elif isinstance(self, RelationshipAggregate):
            logger.debug("Generating instance metadata for RelationshipAggregate: subgraph=%s, relationship=%s",
                         self.subgraph_name, self.relationship_name)

            agg_uri = URIRef(
                NS_HASURA[f"ObjectAggregateRelationship#Agg_{self.subgraph_name}_{self.relationship_name}"])
            logger.debug("Created aggregate URI: %s", agg_uri)

            # Add instance metadata triples
            self._add_property_triples(graph, agg_uri)
            self._add_relationship_triples(graph, agg_uri)

        logger.debug("Completed instance metadata generation. Total triples: %d", len(graph))
        return graph
