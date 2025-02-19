"""
functions.py

This is an example of how you can use the Python SDK's built-in Function connector to easily write Python code.
When you add a Python Lambda connector to your Hasura project, this file is generated for you!

In this file you'll find code examples that will help you get up to speed with the usage of the Hasura lambda connector.
If you are an old pro and already know what is going on you can get rid of these example functions and start writing your own code.
"""

import logging

from hasura_ndc import start
from hasura_ndc.errors import UnprocessableContent
from hasura_ndc.function_connector import FunctionConnector

from hasura_metadata_manager import export_rdf

logger = logging.getLogger(__name__)

connector = FunctionConnector()
logging.basicConfig(level=logging.DEBUG)


@connector.register_query
def metadata_rdf(center_node: str = None, hops: int = None) -> str:
    try:
        return export_rdf(center_node, hops)
    except Exception as e:
        raise UnprocessableContent(message=str(e), details={"Error": repr(e)})


if __name__ == "__main__":
    start(connector)
