import os

from sqlalchemy.orm import sessionmaker

from hasura_metadata_manager.load import create_engine_config
from hasura_metadata_manager.mixins.rdf.model_rdf_mixin import ModelRDFMixin
from hasura_metadata_manager.utilities import rdf_to_advanced_graph

logger = __import__("logging").getLogger(__name__)

def export_model_rdf(center_node=None, hops=None):
    engine = None
    session = None
    try:
        engine = create_engine_config(os.getenv("DATABASE_URL", ''))
        session_factory = sessionmaker(bind=engine)
        session = session_factory()
        assert session is not None, "Session not initialized."

        # Generate model metadata graph
        graph = ModelRDFMixin.generate_model_metadata_graph(session)

        # Serialize the graph to Turtle format
        rdf_output = graph.serialize(format="turtle")

        # Call rdf_to_advanced_graph only if center_node and hops are not None
        if center_node is not None and hops is not None:
            rdf_to_advanced_graph(turtle_data=rdf_output, center_node=center_node, max_hops=hops)

        # Print/log the output
        logger.debug(rdf_output)

        # Return the serialized RDF graph as a string
        return rdf_output

    finally:
        # Ensure proper cleanup
        if session:
            session.close()
        if engine:
            engine.dispose()
