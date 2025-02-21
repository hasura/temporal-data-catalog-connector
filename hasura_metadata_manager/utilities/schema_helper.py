import json
import os
from datetime import datetime
from typing import Any, Optional, Tuple, Set, cast
from typing import Dict

import matplotlib.pyplot as plt
import networkx as nx
from jsonschema import validate  # Import the jsonschema library
from jsonschema.exceptions import ValidationError
from rdflib import Graph, URIRef, RDF, OWL
from rdflib import Literal
from rdflib import plugin
from rdflib.plugins.sparql import prepareQuery
from rdflib.store import Store
from rdflib.term import Node
from sqlalchemy import inspect, text, Table
from sqlalchemy.orm import Session, RelationshipProperty, DeclarativeBase

from ..base import Base
from ..mixins.rdf import RDFGeneratorMixin
from ..mixins.rdf.model_rdf_mixin import ModelRDFMixin
from ..mixins.rdf.namespace import bind_namespaces
from ..supergraph import Supergraph

logger = __import__("logging").getLogger(__name__)
plugin.register('SQLite', Store, 'rdflib.plugins.stores.sqlite', 'SQLite')


class SchemaHelperError(Exception):
    """Custom exception for schema import errors."""
    pass


class SchemaHelper:
    """Imports a schema from a file or JSON data into the database."""

    def __init__(self, session: Session):
        self._schema = None
        assert session is not None, "Session not passed to SchemaHelper"
        self.session = session

    @property
    def engine(self):
        """
        Property to retrieve the engine associated with the session.
        :return: SQLAlchemy Engine instance bound to the session.
        """
        return self.session.get_bind()

    def import_file(self, filename: str) -> Supergraph:
        """Import a schema from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        return self.import_data(data)

    def import_data(self, json_data: Dict[str, Any]) -> Supergraph:
        """Import a schema from a JSON data structure."""

        try:
            # Load the JSON schema
            schema = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'schema.json'), 'r'))

            # Validate the JSON data against the schema
            validate(instance=json_data, schema=schema)
        except FileNotFoundError:
            logger.debug("file not found")
            raise SchemaHelperError("The schema.json file could not be found.")
        except json.JSONDecodeError as e:
            logger.debug(f"Schema file is not valid JSON: {str(e)}")
            raise SchemaHelperError(f"Schema file is not valid JSON: {str(e)}")
        except ValidationError as e:
            logger.debug(f"Invalid input data: {e.message}")
            raise ValueError(f"Invalid input data: {e.message}")
        except Exception as e:
            logger.debug(f"An error occurred: {str(e)}")
            raise Exception(f"An error occurred: {str(e)}")

        try:
            # Create the Supergraph object and disable autoflush
            with self.session.no_autoflush:
                supergraph = Supergraph.from_json(json_data, self.session)
                self.session.flush()  # Flush changes after building the object

            # Commit the transaction to save changes to the database
            self.session.commit()

            # Query the database to retrieve the fully populated Supergraph
            supergraph = cast(Supergraph,
                              self.session.query(Supergraph)
                              .filter_by(name=supergraph.name)  # Assuming Supergraph has an `id` field
                              .one()
                              )

            return supergraph

        except Exception as e:
            # Rollback in case of failure and raise a clear error
            self.session.rollback()
            raise SchemaHelperError(f"Failed to import schema: {str(e)}")

    def cleanup_database(self) -> None:
        """Remove all tables from the database and recreate them."""
        try:
            # Drop all tables
            Base.metadata.drop_all(bind=self.session.get_bind())
            # Recreate all tables
            Base.metadata.create_all(bind=self.session.get_bind())
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to cleanup database: {str(e)}") from e

    def cleanup_database_with_cascade(self) -> None:
        """
        Remove all tables from the database with CASCADE and recreate them.
        Use this if regular cleanup fails due to dependencies.
        """
        try:
            # Get database engine
            engine = self.session.get_bind()

            # logger.debug out registered tables for debugging
            logger.debug("Registered tables:")
            for table_name in Base.metadata.tables:
                logger.debug(table_name)

            # Drop all tables with CASCADE
            inspector = inspect(engine)
            table_names = inspector.get_table_names()

            with engine.connect() as conn:
                # Disable foreign key checks for SQLite (if using SQLite)
                if engine.dialect.name == 'sqlite':
                    conn.execute(text("PRAGMA foreign_keys=OFF"))

                # Drop all tables with CASCADE
                for table in table_names:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))

                # Re-enable foreign key checks for SQLite
                if engine.dialect.name == 'sqlite':
                    conn.execute(text("PRAGMA foreign_keys=ON"))

                conn.commit()

            # Recreate all tables
            Base.metadata.create_all(bind=engine)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to cleanup database with cascade: {str(e)}") from e

    def update_file(self, filename: str) -> Supergraph:
        """
        Updates the schema from a file if the file's updated timestamp is newer
        than the Supergraph's created_date.

        :param filename: Path to the JSON file to be checked and imported
        :return: Updated Supergraph object if the update occurs
        :raises SchemaImportError: If the operation fails
        """
        # Get the file's last modified date
        try:
            file_last_modified = datetime.fromtimestamp(os.path.getmtime(filename))
        except FileNotFoundError:
            raise SchemaHelperError(f"The file '{filename}' could not be found.")

        # Fetch the latest Supergraph from the database
        supergraph: Optional[Supergraph] = self.session.query(Supergraph).order_by(
            Supergraph.t_created_at.desc()).first()

        # Check if the file is newer than the Supergraph's creation date
        if supergraph is not None and supergraph.t_created_at >= file_last_modified:
            logger.debug("File is not newer than the current Supergraph. No update performed.")
            return supergraph

        # If the file is newer or no Supergraph exists, import the new schema
        logger.debug("File is newer than the current Supergraph (or none exists). Updating schema...")
        return self.import_file(filename)

    @staticmethod
    def is_join_table(clazz) -> bool:
        """
        Detect if the given SQLAlchemy mapped class represents a join/association table.

        A join table typically:
        1. Has no attributes other than foreign key columns.
        2. Does not define meaningful primary key columns beyond composite keys.
        3. Is used as the `secondary` table in a many-to-many relationship.

        :param clazz: SQLAlchemy mapped class
        :return: True if the class is a join/association table, False otherwise.
        """
        # Get the table object associated with the class
        table = clazz.__table__

        def get_mixin_columns(clazz) -> set:
            """
            Get all column names defined in mixins for a given SQLAlchemy class.
            """
            mixin_columns = set()

            # Loop through the class's base classes (mixins included)
            for base in clazz.__bases__:
                if hasattr(base, "__annotations__") and not issubclass(base,
                                                                       DeclarativeBase):  # Check for SQLAlchemy-like mixins
                    mixin_columns.update(base.__annotations__.keys())

            return mixin_columns

            # Dynamically get all mixin columns

        mixin_columns = get_mixin_columns(clazz)

        # Check if the table has any meaningful (non-foreign key) columns
        has_meaningful_columns = any(
            not col.foreign_keys and not col.primary_key
            and col.name not in mixin_columns
            for col in table.columns
        )

        # If no meaningful columns are found, this is likely a join table
        if not has_meaningful_columns:
            return True

        # Iterate over relationships and check for `secondary` usage
        for mapper in Base.registry.mappers:
            for relationship in mapper.relationships.values():  # Ensure you're iterating correctly
                if isinstance(relationship, RelationshipProperty):
                    if relationship.secondary is not None and isinstance(relationship.secondary,
                                                                         Table) and table.name == relationship.secondary.name:
                        return True

        # If none of the above checks match, it's not a join table
        return False

    def generate_rdf_definitions(self) -> Graph:
        """
        Generate a combined RDF graph for all SQLAlchemy models
        that include the RDFGeneratorMixin, while excluding join tables.

        :return: A single RDFLib Graph containing triples from all models.
        """
        # Initialize a combined RDF graph
        combined_graph = Graph(identifier="hasura_metadata_manager")
        bind_namespaces(combined_graph)

        # Iterate over all mapped classes in declarative `Base`
        for mapper in Base.registry.mappers:
            clazz = mapper.class_

            # Check if the class has the RDFGeneratorMixin
            if issubclass(clazz, RDFGeneratorMixin):
                logger.debug(f"Generating RDF graph for {clazz.__name__}")
                # Generate RDF data for this class and its instances
                class_graph = clazz.translate_to_instance_metadata(
                    self.session)  # Generate RDF graph for class instances
                combined_graph += class_graph  # Merge class graph into combined graph

        return combined_graph

    def generate_model_rdf_definitions(self) -> Graph:
        """
        Generate a combined RDF graph for all SQLAlchemy models
        that include the RDFGeneratorMixin, while excluding join tables.

        :return: A single RDFLib Graph containing triples from all models.
        """
        # Initialize a combined RDF graph
        combined_graph = Graph(identifier="models")
        bind_namespaces(combined_graph)

        # Iterate over all mapped classes in declarative `Base`
        for mapper in Base.registry.mappers:
            clazz = mapper.class_

            # Check if the class has the RDFGeneratorMixin
            if issubclass(clazz, ModelRDFMixin):
                logger.debug(f"Generating RDF graph for {clazz.__name__}")
                # Generate RDF data for this class and its instances
                class_graph = clazz.translate_to_model_metadata(
                    self.session)  # Generate RDF graph for class instances
                combined_graph += class_graph  # Merge class graph into combined graph

        return combined_graph

    @staticmethod
    def filter_graph_by_sparql(graph: Graph, start_node: URIRef, max_hops: int) -> Graph:
        """
        Filters the input RDF graph using a SPARQL CONSTRUCT query starting from a node, with a limit on hops.
        """
        where_patterns = []
        construct_patterns = []

        # Add base patterns for direct relationships
        where_patterns.extend([
            "{ ?s ?p ?target }",
            "{ ?target ?p ?o }"
        ])
        construct_patterns.append("?s ?p ?o")

        # Add patterns for each additional hop
        for i in range(1, max_hops + 1):
            # Forward direction
            where_patterns.append(
                f"{{ ?target ?p1_{i} ?o1_{i} . ?o1_{i} ?p2_{i} ?o2_{i} }}"
            )
            construct_patterns.append(f"?o1_{i} ?p2_{i} ?o2_{i}")

            # Reverse direction
            where_patterns.append(
                f"{{ ?s1_{i} ?p1_{i} ?target . ?s2_{i} ?p2_{i} ?s1_{i} }}"
            )
            construct_patterns.append(f"?s2_{i} ?p2_{i} ?s1_{i}")

        # Build construct and where clauses
        construct_clause = " .\n        ".join(construct_patterns)
        where_clause = " } UNION { ".join(where_patterns)

        # Create parameterized query
        query_str = (
            f"CONSTRUCT {{ {construct_clause} }} "
            f"WHERE {{ ?s ?p ?o . {{ {where_clause} }} }}"
        )

        logger.debug(f"Constructed SPARQL Query:\n{query_str}")

        try:
            # Prepare the query once
            prepared_query = prepareQuery(query_str)
            # Execute with bindings
            result = graph.query(prepared_query, initBindings={'target': start_node})

            result_graph = Graph()
            bind_namespaces(graph)
            for triple in result:
                result_graph.add(triple)
            return result_graph
        except Exception as e:
            logger.debug(f"Error during SPARQL execution: {e}")
            return Graph()

    def generate_rdf_definitions_for_classes(self) -> Graph:
        """
        Generate a combined RDF graph for all SQLAlchemy models
        that include the RDFGeneratorMixin, while excluding join tables.
        """
        # Initialize a combined RDF graph
        combined_graph = Graph(identifier="supergraph")
        bind_namespaces(combined_graph)

        # Iterate over all mapped classes in declarative `Base`
        for mapper in Base.registry.mappers:
            clazz = mapper.class_

            # Skip join tables
            if self.is_join_table(clazz):
                logger.debug(f"Skipping join table {clazz.__name__}")
                continue

            # Check if the class has ModelRDFMixin
            if issubclass(clazz, ModelRDFMixin):
                logger.debug(f"Generating RDF model hasura_metadata_manager for {clazz.__name__}")
                # Generate only model hasura_metadata_manager using ModelRDFMixin
                model_graph = clazz.translate_to_model_metadata(self.session)
                combined_graph += model_graph

        return combined_graph

    @staticmethod
    def compact_uri(node):
        """Helper function to get the local name of an RDF node."""
        if isinstance(node, URIRef):  # Only process URIRefs
            return str(node).split('/')[-1].split('#')[-1]
        elif isinstance(node, Literal):  # For literals, return as-is
            return str(node)
        else:  # Handle BNodes or other node types
            return str(node)

    def visualize_graph_networkx(self, graph: Graph):
        G = nx.DiGraph()  # Create a directed graph

        # Add nodes and edges with compact URIs
        for subj, pred, obj in graph:
            subj_label = self.compact_uri(subj)
            pred_label = self.compact_uri(pred)
            obj_label = self.compact_uri(obj)

            if pred_label.startswith("has"):
                G.add_edge(subj_label, obj_label, label="")

        # Draw the graph
        pos = nx.spring_layout(G)  # Layout algorithm
        plt.figure(figsize=(10, 8))
        nx.draw(G, pos, with_labels=True, node_color="lightblue", node_size=3000, font_size=10)
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels={(u, v): d["label"] for u, v, d in G.edges(data=True)}
        )
        plt.title("RDF Graph Visualization")
        plt.show()

    from rdflib import Graph, Namespace
    from typing import Tuple

    @staticmethod
    def convert_to_bidirectional(
            g: Graph,
            custom_ns: Namespace,
            suffixes: Tuple[str, str] = ("#Many", "#One"),
            bidirectional_name: str = "hasBidirectionalRelation"
    ) -> None:
        """
        Find all mutual relationships with the given complementary suffixes and convert them to bidirectional relationships,
        modifying the graph in place.

        Args:
            g: Input RDF graph to modify
            custom_ns: Custom namespace for your ontology
            suffixes: Tuple of two suffixes to look for (e.g., ("#Many", "#One"))
            bidirectional_name: Name of the new bidirectional relationship (e.g., "hasFriend")
        """
        suffix1, suffix2 = suffixes

        # Find all relationships containing either suffix
        matching_rels: Set[Tuple[Node, Node, Node]] = set()
        for s, p, o in g:
            if suffix1 in str(p) or suffix2 in str(p):
                matching_rels.add((s, p, o))

        # Find mutual relationships
        mutual_pairs: Set[Tuple[Node, Node]] = set()
        for s1, p1, o1 in matching_rels:
            for s2, p2, o2 in matching_rels:
                # Check if there's a relationship in the opposite direction
                if s1 == o2 and o1 == s2:
                    # Verify the relationships have complementary suffixes
                    p1_has_suffix1 = suffix1 in str(p1)
                    p2_has_suffix1 = suffix1 in str(p2)
                    # Only add if they have different suffixes
                    if p1_has_suffix1 != p2_has_suffix1:
                        # Store the pair in a canonical order to avoid duplicates
                        sorted_nodes = sorted([s1, o1], key=str)
                        pair: Tuple[Node, Node] = (sorted_nodes[0], sorted_nodes[1])
                        mutual_pairs.add(pair)

        # Create bidirectional relationship
        bidirectional_rel = getattr(custom_ns, bidirectional_name)

        # Define it as a symmetric property
        g.add((bidirectional_rel, RDF.type, OWL.SymmetricProperty))

        # Add bidirectional relationships and remove original relationships
        for entity1, entity2 in mutual_pairs:
            # Add new bidirectional relationship
            g.add((entity1, bidirectional_rel, entity2))

            # Remove the original suffixed relationships between these entities
            for s, p, o in matching_rels:
                if (s == entity1 and o == entity2) or (s == entity2 and o == entity1):
                    g.remove((s, p, o))
