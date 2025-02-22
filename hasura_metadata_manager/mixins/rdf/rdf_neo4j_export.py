import os
from abc import abstractmethod
from contextlib import contextmanager
from functools import wraps
from typing import Optional, Dict, Any, List, Tuple, overload

from rdflib import URIRef, Graph, RDF
from rdflib_neo4j import Neo4jStore, Neo4jStoreConfig, HANDLE_VOCAB_URI_STRATEGY
from sqlalchemy.orm import Session

from . import NS_HASURA, NS_HASURA_PROP, NS_HASURA_REL, NS_HASURA_OBJ_REL, NS_HASURA_MODEL
from .namespace import bind_namespaces, NS_HASURA_SUBGRAPH, NS_HASURA_SUPERGRAPH
from .rdf_translator import RDFTranslator, T

logger = __import__("logging").getLogger(__name__)

# Global configuration for Neo4j
_GLOBAL_NEO4J_CONFIG: Optional[Dict[str, Any]] = None


def check_neo4j_config(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _GLOBAL_NEO4J_CONFIG:
            logger.warning(f"Neo4j not configured when calling {func.__name__}. Call configure_neo4j first.")
        return func(*args, **kwargs)

    return wrapper


class RDFNeo4jExport:
    """Abstract base class for Neo4j export capabilities"""

    @abstractmethod
    def to_rdf_graph(self) -> Graph:
        """Must be implemented by classes using this mixin"""
        pass

    @abstractmethod
    def _get_subject_uri(self) -> URIRef:
        """Must be implemented by classes using this mixin"""
        pass

    @classmethod
    @overload
    @abstractmethod
    def generate_rdf_graph(cls, session: Session, metadata_type: str, translator: RDFTranslator[T] = None) -> T:
        """Must be implemented by classes using this mixin"""
        pass

    @classmethod
    @abstractmethod
    def generate_rdf_graph(cls, session: Session, metadata_type: str, translator: RDFTranslator[T] = None) -> T:
        """Must be implemented by classes using this mixin"""
        pass

    @classmethod
    @abstractmethod
    def get_rdf_type(cls) -> URIRef:
        """Must be implemented by classes using this mixin"""
        pass

    @classmethod
    def configure_neo4j(
            cls,
            uri: str = 'bolt://localhost:7687',
            database: str = 'neo4j',
            auth: tuple = ('neo4j', 'password'),
            batch_size: int = 5000,
            custom_prefixes: Optional[Dict[str, str]] = None,
            custom_mappings: Optional[List[Tuple[str, str, str]]] = None,
            multival_props_names: Optional[List[Tuple[str, str]]] = None
    ) -> None:
        """Configure Neo4j connection details"""
        # Replace 'auth': auth, with the following logic:
        neo4j_auth_env = os.getenv('NEO4J_AUTH', None)

        if custom_prefixes is None:
            custom_prefixes = {
                "has": str(NS_HASURA),
                "prop": str(NS_HASURA_PROP),
                "rel": str(NS_HASURA_REL),
                "drel": str(NS_HASURA_OBJ_REL),
                "mod": str(NS_HASURA_MODEL),
                "sub": str(NS_HASURA_SUBGRAPH),
                "sup": str(NS_HASURA_SUPERGRAPH)
            }
        if custom_mappings is None:
            custom_mappings = [
                # Format: (namespace, neo4j_label, property_name)
                ("mod", None, None),
                ("sub", "Subgraph", None),
                ("sup", "Supergraph", None),
                ("prop", "Property", None)
            ]

        if neo4j_auth_env:
            try:
                username, password = neo4j_auth_env.split(",", 1)  # Split into a tuple (username, password)
                auth = (username.strip(), password.strip())  # Assign the tuple
            except ValueError:
                raise ValueError("NEO4J_AUTH must be in the format 'username,password'")
        else:
            auth = auth  # Fallback to the original `auth` value
        global _GLOBAL_NEO4J_CONFIG
        _GLOBAL_NEO4J_CONFIG = {
            'uri': os.getenv("NEO4J_URI", uri),
            'database': os.getenv("NEO4J_DATABASE", database),
            'auth': auth,
            'batch_size': batch_size,
            'handle_vocab_uri_strategy': HANDLE_VOCAB_URI_STRATEGY.IGNORE,
            'custom_prefixes': custom_prefixes,
            'custom_mappings': custom_mappings or [],
            'multival_props_names': multival_props_names or []
        }
        logger.info(f"Configured Neo4j connection to {uri}")

    @contextmanager
    @check_neo4j_config
    def _neo4j_graph(self, config: Optional[Dict[str, Any]] = None) -> Graph:
        """Context manager for Neo4j graph connection"""
        neo4j_config = config or _GLOBAL_NEO4J_CONFIG
        if not neo4j_config:
            raise RuntimeError("Neo4j configuration not set. Call configure_neo4j first.")

        # Create auth data dictionary
        auth_data = {
            'uri': neo4j_config['uri'],
            'database': neo4j_config['database'],
            'user': neo4j_config['auth'][0],
            'pwd': neo4j_config['auth'][1]
        }

        # Create Neo4j store configuration
        store_config = Neo4jStoreConfig(
            auth_data=auth_data,
            batching=True,
            batch_size=neo4j_config['batch_size'],
            handle_vocab_uri_strategy=neo4j_config['handle_vocab_uri_strategy'],
            custom_prefixes=neo4j_config['custom_prefixes'],
            custom_mappings=neo4j_config['custom_mappings'],
            multival_props_names=neo4j_config['multival_props_names']
        )

        # Create Neo4j store with configuration
        store = Neo4jStore(store_config)

        # Create graph with Neo4j store
        graph = Graph(store=store)
        bind_namespaces(graph)

        try:
            yield graph
        finally:
            # Close the store connection
            store.close()

    @classmethod
    @check_neo4j_config
    def _clear_subject_from_neo4j(cls, neo4j_graph: Graph, subject_uri: URIRef) -> None:
        """Remove all triples for a given subject from Neo4j"""
        # Get the Neo4j store from the graph
        store = neo4j_graph.store
        if not isinstance(store, Neo4jStore):
            raise RuntimeError("Graph does not use Neo4jStore")

        # Use store's remove_node method if available, otherwise fallback to triples
        if hasattr(store, 'remove_node'):
            store.remove_node(subject_uri)
            logger.debug(f"Removed node {subject_uri} from Neo4j")
        else:
            existing_triples = list(neo4j_graph.triples((subject_uri, None, None)))
            for triple in existing_triples:
                neo4j_graph.remove(triple)
            logger.debug(f"Cleared {len(existing_triples)} existing triples for {subject_uri}")

    @check_neo4j_config
    def sync_to_neo4j(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Sync this instance's RDF data to Neo4j (handles updates/deletes)"""
        source_graph = self.to_rdf_graph()
        subject_uri = self._get_subject_uri()

        with self._neo4j_graph(config) as neo4j_graph:
            self._clear_subject_from_neo4j(neo4j_graph, subject_uri)

            # Get Neo4j store for direct access if needed
            store = neo4j_graph.store
            if not isinstance(store, Neo4jStore):
                raise RuntimeError("Graph does not use Neo4jStore")

            # Add triples to Neo4j
            for triple in source_graph:
                store.add(triple)  # Use store directly for better performance

            logger.debug(f"Synced {len(source_graph)} triples to Neo4j for {self.__class__.__name__}")

    @classmethod
    @check_neo4j_config
    def sync_all_to_neo4j(
            cls,
            session: Session,
            source_graph: Graph,
            config: Optional[Dict[str, Any]] = None,
            batch_size: int = 1000
    ) -> None:
        """Sync all instances' RDF data to Neo4j (handles updates/deletes)"""
        config = config or _GLOBAL_NEO4J_CONFIG

        with cls._neo4j_graph(config) as neo4j_graph:
            store = neo4j_graph.store
            if not isinstance(store, Neo4jStore):
                raise RuntimeError("Graph does not use Neo4jStore")

            # Find existing subjects in Neo4j for this class
            existing_subjects = set()
            for s, _, _ in store.triples((None, RDF.type, cls.get_rdf_type())) or {}:
                existing_subjects.add(s)

            # Get current subjects from the source graph
            current_subjects = {s for s, _, _ in source_graph.triples((None, RDF.type, cls.get_rdf_type()))}

            # Remove subjects that no longer exist
            for subject in existing_subjects - current_subjects:
                uri_subject = URIRef(str(subject))
                cls._clear_subject_from_neo4j(neo4j_graph, uri_subject)
                logger.debug(f"Removed deleted subject {uri_subject} from Neo4j")

            # Process current triples in batches
            triples = list(source_graph)
            for i in range(0, len(triples), batch_size):
                batch = triples[i:i + batch_size]
                # Use store's batch_add if available
                if hasattr(store, 'batch_add'):
                    store.batch_add(batch)
                else:
                    for triple in batch:
                        store.add(triple)
                    logger.debug(f"Synced batch of {len(batch)} triples to Neo4j")

            logger.debug(f"Completed sync of {len(triples)} triples to Neo4j for {cls.__name__}")

    @check_neo4j_config
    def delete_from_neo4j(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Remove this instance's data from Neo4j"""
        subject_uri = self._get_subject_uri()
        with self._neo4j_graph(config) as neo4j_graph:
            self._clear_subject_from_neo4j(neo4j_graph, subject_uri)
            logger.debug(f"Deleted {subject_uri} from Neo4j")
