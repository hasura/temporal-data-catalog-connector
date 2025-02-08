import json
import logging
import subprocess
import warnings
from typing import List, TYPE_CHECKING, cast

import pytest
from rdflib import Graph, URIRef
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..compatibility_config import CompatibilityConfig
from ..mixins.rdf import NS_HASURA, NS_HASURA_OBJ_REL, bind_namespaces
from ..model import Model
from ..relationship import Relationship
from ..utilities import SchemaHelper, compare_json_files, rdf_to_advanced_graph

if TYPE_CHECKING:
    from ..boolean_expression_type import BooleanExpressionType
    from .. import ModelPermission, ObjectType, Supergraph, Subgraph, init_with_session
    from ..aggregate_expression import AggregateExpression
    from ..data_connector.schema.scalar_type.scalar_type import ScalarType
    from ..data_connector_scalar_representation.data_connector_scalar_representation import \
        DataConnectorScalarRepresentation

# Tell pytest to show warnings
pytestmark = pytest.mark.filterwarnings("always")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.fixture(autouse=True)
def clean_directory():
    """
    Run the `dot_clean -v .` command before each test to clean up directory.
    This function ensures the tests will proceed even if the command fails.
    This is for when you have installed your project on macOS with a fat32 drive.
    """
    try:
        # Execute the shell command to clean . and suppress any errors
        logger.debug("Executing `dot_clean -v .` before running the test...")
        result = subprocess.run(["dot_clean", "-v", "."], capture_output=True, text=True)
        logger.debug(result.stdout)  # Print the output of the command
        if result.returncode != 0:
            logger.debug(f"Warning: `dot_clean` returned a non-zero exit code: {result.returncode}")
    except FileNotFoundError:
        logger.debug("The `dot_clean` command is not available. Make sure you are running this on a macOS system.")
    except Exception as e:
        logger.debug(f"An unexpected error occurred while running `dot_clean`: {str(e)}")
    finally:
        logger.debug("Continuing with tests regardless of `dot_clean` success or failure.")


@pytest.fixture
def session():
    database_url = "postgresql://kenstott:rN8qOh6AEMCP@ep-yellow-salad-961725.us-west-2.aws.neon.tech/hasura_config?sslmode=require"  # Example: SQLite database stored in a file
    engine = create_engine(database_url)
    return sessionmaker(bind=engine)()


def test_export_ddn_rdf(session):
    from ..supergraph import Supergraph

    Supergraph.configure_neo4j()
    si = SchemaHelper(session)
    graph = si.generate_rdf_definitions_for_classes()
    Supergraph.sync_all_to_neo4j(session=session, source_graph=graph)

    # Serialize the graph to Turtle format
    rdf_output = graph.serialize(format="turtle")
    rdf_to_advanced_graph(turtle_data=rdf_output, center_node="Supergraph", max_hops=2)

    # Print the output to the console
    logger.debug(rdf_output)

    # Write the output to a file named 'ddn.txt'
    with open("./ddn.ttl", "w") as file:
        file.write(rdf_output)


def test_export_rdf(session):
    from ..supergraph import Supergraph

    Supergraph.configure_neo4j()
    si = SchemaHelper(session)
    graph = si.generate_rdf_definitions()
    assert len(graph) > 0
    si.convert_to_bidirectional(graph, NS_HASURA, ("#HAS_MANY", "#HAS_ONE"), "HAS")
    # Write the output to a file named 'ddn.ttl'
    rdf_output = graph.serialize(format="turtle")
    with open("./ddn-instance.ttl", "w") as file:
        file.write(rdf_output)
    Supergraph.sync_all_to_neo4j(session=session, source_graph=graph)
    logger.debug(rdf_output)


def test_export_node_from_rdf(session):
    si = SchemaHelper(session)
    graph = Graph()
    bind_namespaces(graph)
    graph.parse("ddn-instance.ttl", format="turtle")

    # Print namespace bindings and some sample triples for debugging
    for s, p, o in graph.triples((None, None, URIRef(NS_HASURA["ObjectType/app_Track"]))):
        logger.debug(f"Found triple: {s} {p} {o}")

    # Try with the colon prefix version
    start_node = URIRef(NS_HASURA["ObjectType/app_Track"])

    # Let's also logger.debug out a sample triple directly using the graph API
    # This will help us see exactly how RDFLib is representing these nodes internally
    logger.debug("Direct graph access:")
    sample_triple = next(graph.triples((None, None, start_node)), None)
    if sample_triple:
        logger.debug(f"Sample triple found: {sample_triple}")
        logger.debug(f"URI type: {type(start_node)}")
        logger.debug(f"URI string representation: {str(start_node)}")
        logger.debug(f"URI n3 representation: {start_node.n3()}")

    reduced = si.filter_graph_by_sparql(graph, start_node, 3)
    reduced_output = reduced.serialize(format="turtle")
    with open("./ddn-instance-node.ttl", "w") as file:
        file.write(reduced_output)


def filter_graph_by_sparql(graph, start_node, max_hops, predicate_filter=None):
    """
    Filter RDF graph using multi-hop traversal and predicate filtering.

    Args:
        graph: The source RDF graph
        start_node: Starting node URI
        max_hops: Maximum number of hops to traverse
        predicate_filter: Optional list of predicates to include, or None for all
    """

    def get_outgoing_query(hops):
        # Build nested pattern for multiple hops
        patterns = []
        filters = []
        constructs = []

        # First hop pattern is always direct from start node
        patterns.append(f"<{start_node}> ?p1 ?o1 .")
        constructs.append(f"<{start_node}> ?p1 ?o1 .")
        if predicate_filter:
            filters.append("FILTER(" + " || ".join(f"?p1 = <{pred}>" for pred in predicate_filter) + ")")

        # Add patterns for additional hops
        for i in range(2, hops + 1):
            prev = i - 1
            patterns.append(f"OPTIONAL {{ ?o{prev} ?p{i} ?o{i} . }}")
            constructs.append(f"?o{prev} ?p{i} ?o{i} .")
            if predicate_filter:
                filters.append(f"FILTER(!BOUND(?p{i}) || " +
                               " || ".join(f"?p{i} = <{pred}>" for pred in predicate_filter) + ")")

        pattern_str = "\n            ".join(patterns)
        filter_str = "\n            ".join(filters)
        construct_str = "\n            ".join(constructs)

        return f"""
        CONSTRUCT {{
            {construct_str}
        }}
        WHERE {{
            {pattern_str}
            {filter_str}
        }}"""

    def get_incoming_query(hops):
        # Similar to outgoing but reversed direction
        patterns = []
        filters = []
        constructs = []

        # First hop pattern for incoming
        patterns.append(f"?s1 ?p1 <{start_node}> .")
        constructs.append(f"?s1 ?p1 <{start_node}> .")
        if predicate_filter:
            filters.append("FILTER(" + " || ".join(f"?p1 = <{pred}>" for pred in predicate_filter) + ")")

        # Add patterns for additional hops
        for i in range(2, hops + 1):
            prev = i - 1
            patterns.append(f"OPTIONAL {{ ?s{i} ?p{i} ?s{prev} . }}")
            constructs.append(f"?s{i} ?p{i} ?s{prev} .")
            if predicate_filter:
                filters.append(f"FILTER(!BOUND(?p{i}) || " +
                               " || ".join(f"?p{i} = <{pred}>" for pred in predicate_filter) + ")")

        pattern_str = "\n            ".join(patterns)
        filter_str = "\n            ".join(filters)
        construct_str = "\n            ".join(constructs)

        return f"""
        CONSTRUCT {{
            {construct_str}
        }}
        WHERE {{
            {pattern_str}
            {filter_str}
        }}"""

    try:
        result_graph = Graph()

        # Bind namespaces
        bind_namespaces(result_graph)

        # Get outgoing relationships with multiple hops
        logger.debug(f"Executing {max_hops}-hop outgoing relationships query...")
        outgoing_query = get_outgoing_query(max_hops)
        logger.debug(f"Outgoing query:\n{outgoing_query}")
        result_graph += graph.query(outgoing_query).graph
        logger.debug(f"Found {len(result_graph)} triples from outgoing relationships")

        # Get incoming relationships with multiple hops
        logger.debug(f"Executing {max_hops}-hop incoming relationships query...")
        incoming_query = get_incoming_query(max_hops)
        logger.debug(f"Incoming query:\n{incoming_query}")
        result_graph += graph.query(incoming_query).graph
        logger.debug(f"Total of {len(result_graph)} triples after adding incoming relationships")

        return result_graph

    except Exception as e:
        logger.error(f"SPARQL query failed: {str(e)}")
        logger.debug(f"Graph size: {len(graph)}")
        logger.debug(f"Start node: {start_node}")
        raise


def test_export_node_from_rdf2(session):
    graph = Graph()
    bind_namespaces(graph)
    graph.parse("ddn-instance.ttl", format="turtle")

    logger.debug(f"Total number of triples in graph: {len(graph)}")

    start_node = URIRef("http://hasura.com/ontology/ObjectType/app_Track")
    logger.debug(f"Looking for triples with start node: {start_node}")

    # Define predicate filters if needed
    predicate_filter = [
        NS_HASURA_OBJ_REL.Array,
        NS_HASURA_OBJ_REL.Object,
    ]

    try:
        # Execute with multi-hop query and predicate filter
        reduced = filter_graph_by_sparql(
            graph,
            start_node,
            max_hops=3,
            predicate_filter=predicate_filter
        )

        # Write results
        reduced_output = reduced.serialize(format="turtle")
        with open("../ddn-instance-node.ttl", "w") as file:
            file.write(reduced_output)

        logger.debug(f"Successfully processed graph. Found {len(reduced)} triples")

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise


def test_container_init(session):
    from .. import init_with_session
    init_with_session(clean_database=True)


def test_schema_import(session, clean_database=True,
                       engine_build: str = './example/engine/build/metadata.json'):  # Add flag to control cleanup
    # Capture and logger.debug warnings
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered
        warnings.simplefilter("always")

        importer = SchemaHelper(session)

        # Only cleanup if flag is set
        if clean_database:
            importer.cleanup_database_with_cascade()

        supergraph = importer.import_file(engine_build)

        assert supergraph.name == "default"
        assert supergraph.version == "v2"

        # Register temporal views after schema is loaded
        from ..mixins.temporal import register_temporal_views
        from ..base.core_base import CoreBase

        register_temporal_views(CoreBase, engine=importer.engine)

        from .. import ModelPermission, ObjectType, Supergraph, Subgraph
        from ..aggregate_expression import AggregateExpression
        from ..auth_config import AuthConfig
        from ..data_connector.schema.scalar_type.scalar_type import ScalarType
        from ..data_connector_scalar_representation.data_connector_scalar_representation import \
            DataConnectorScalarRepresentation

        # Get all AggregateExpressions and convert to JSON
        aggregate_expressions = cast(List[AggregateExpression], session.query(AggregateExpression).all())
        json_output = [agg.to_json() for agg in aggregate_expressions]

        # Write to file
        output_path = './aggregate_expressions.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} aggregate expressions to {output_path}")

        # Get all AuthConfig and convert to JSON
        auth_configs = cast(List[AuthConfig], session.query(AuthConfig).all())
        json_output = [auth_config.to_json() for auth_config in auth_configs]

        # Write to file
        output_path = './auth_configs.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} auth configs to {output_path}")

        # Get all ScalarTypes and convert to JSON
        scalar_types = cast(List[ScalarType], session.query(ScalarType).all())
        json_output = [agg.to_json() for agg in scalar_types]

        # Write to file
        output_path = './scalar_types.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        # Get all BooleanExpressionTypes and convert to JSON
        from ..boolean_expression_type import BooleanExpressionType
        boolean_expression_types = cast(List[BooleanExpressionType], session.query(BooleanExpressionType).all())
        json_output = [agg.to_json() for agg in boolean_expression_types]

        # Write to file
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} boolean expression types to {output_path}")

        # Get all CompatibilityConfigs and convert to JSON
        compatibility_configs = cast(List[CompatibilityConfig], session.query(CompatibilityConfig).all())
        json_output = [agg.to_json() for agg in compatibility_configs]

        # Write to file
        output_path = './compatibility_configs.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} compatibility configs to {output_path}")

        # Get all ModelPermissions and convert to JSON
        model_permissions: List[ModelPermission] = cast(List[ModelPermission], session.query(ModelPermission).all())
        json_output = [agg.to_json() for agg in model_permissions]

        # Write to file
        output_path = './model_permissions.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} model permissions to {output_path}")

        # Get all Relationships and convert to JSON
        relationships = cast(List[Relationship], session.query(Relationship).all())
        json_output = [agg.to_json() for agg in relationships]

        # Write to file
        output_path = './relationships.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} relationships to {output_path}")

        # Get all Models and convert to JSON
        models = cast(List[Model], session.query(Model).all())
        json_output = [agg.to_json() for agg in models]

        # Write to file
        output_path = './models.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} models to {output_path}")

        # Get all ObjectTypes and convert to JSON
        object_types = cast(List[ObjectType], session.query(ObjectType).all())
        json_output = [agg.to_json() for agg in object_types]

        # Write to file
        output_path = './object_types.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} object types to {output_path}")

        # Get all DataConnectorScalarRepresentations and convert to JSON
        object_types = cast(List[DataConnectorScalarRepresentation],
                            session.query(DataConnectorScalarRepresentation).all())
        json_output = [agg.to_json() for agg in object_types]

        # Write to file
        output_path = './data_connector_scalar_representations.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} data connector scalar representations to {output_path}")

        # Get all Subgraphs and convert to JSON
        subgraphs = cast(List[Subgraph], session.query(Subgraph).all())
        json_output = [agg.to_json(session) for agg in subgraphs]

        # Write to file
        output_path = './subgraphs.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} subgraphs to {output_path}")

        # Get all Supergraphs and convert to JSON
        supergraph = cast(List[Supergraph], session.query(Supergraph).all())[0]
        json_output = supergraph.to_json(session)

        # Write to file
        output_path = './supergraph.json'
        with open(output_path, 'w') as f:
            json.dump(json_output, f, indent=2)

        logger.debug(f"\nWrote {len(json_output)} supergraph to {output_path}")

        # Compare files
        is_equal, differences = compare_json_files('./example/engine/build/metadata.json', 'supergraph.json', [
            "kind;definition.sourceType;definition.name",
            "kind;definition.name",
            "kind;definition.modelName",
            "kind;definition.typeName",
            "kind;definition.dataConnectorScalarType",
            "name", "id", "key"
        ])
        logger.debug(f"Files are equivalent: {is_equal}")
        if not is_equal:
            logger.debug("Differences found:")
            for diff in differences:
                logger.debug(f"- {diff}")

        # Print any warnings that were captured
        if len(w) > 0:
            logger.debug("\nWarnings during test:")
            for warning in w:
                logger.debug(f"Warning: {warning.message}")
