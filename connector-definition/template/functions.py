"""
functions.py

This is an example of how you can use the Python SDK's built-in Function connector to easily write Python code.
When you add a Python Lambda connector to your Hasura project, this file is generated for you!

In this file you'll find code examples that will help you get up to speed with the usage of the Hasura lambda connector.
If you are an old pro and already know what is going on you can get rid of these example functions and start writing your own code.
"""
from __future__ import annotations

from hasura_ndc import start
from hasura_ndc.instrumentation import with_active_span # If you aren't planning on adding additional tracing spans, you don't need this!
from opentelemetry.trace import get_tracer # If you aren't planning on adding additional tracing spans, you don't need this either!
from hasura_ndc.function_connector import FunctionConnector
from pydantic import BaseModel, Field # You only need this import if you plan to have complex inputs/outputs, which function similar to how frameworks like FastAPI do
import asyncio # You might not need this import if you aren't doing asynchronous work
from hasura_ndc.errors import UnprocessableContent
from typing import Annotated

connector = FunctionConnector()

# This is an example of a simple function that can be added onto the graph
@connector.register_query # This is how you register a query
def hello(name: str) -> str:
    return f"Hello {name}"

# You can use Nullable parameters, but they must default to None
# The FunctionConnector also doesn't care if your functions are sync or async, so use whichever you need!
@connector.register_query
async def nullable_hello(name: str | None = None) -> str:
    return f"Hello {name if name is not None else 'world'}"

# Parameters that are untyped accept any scalar type, arrays, or null and are treated as JSON.
# Untyped responses or responses with indeterminate types are treated as JSON as well!
@connector.register_mutation # This is how you register a mutation
def some_mutation_function(any_type_param):
    return any_type_param

# Similar to frameworks like FastAPI, you can use Pydantic Models for inputs and outputs
class Pet(BaseModel):
    name: str

class Person(BaseModel):
    name: str
    pets: list[Pet] | None = None

@connector.register_query
def greet_person(person: Person) -> str:
    greeting = f"Hello {person.name}!"
    if person.pets is not None:
        for pet in person.pets:
            greeting += f" And hello to {pet.name}.."
    else:
        greeting += f" I see you don't have any pets."
    return greeting

class ComplexType(BaseModel):
    lists: list[list] # This turns into a List of List's of any valid JSON!
    person: Person | None = None # This becomes a nullable attribute that accepts a person type from above
    x: int # You can also use integers
    y: float # As well as floats
    z: bool # And booleans

# When the outputs are typed with Pydantic models you can select which attributes you want returned!
@connector.register_query
def complex_function(input: ComplexType) -> ComplexType:
    return input

# This last section shows you how to add Otel tracing to any of your functions!
tracer = get_tracer("ndc-sdk-python.server") # You only need a tracer if you plan to add additional Otel spans

# Utilizing with_active_span allows the programmer to add Otel tracing spans
@connector.register_query
async def with_tracing(name: str) -> str:

    def do_some_more_work(_span, work_response):
        return f"Hello {name}, {work_response}"

    async def the_async_work_to_do():
        # This isn't actually async work, but it could be! Perhaps a network call belongs here, the power is in your hands fellow programmer!
        return "That was a lot of work we did!"

    async def do_some_async_work(_span):
        work_response = await the_async_work_to_do()
        return await with_active_span(
            tracer,
            "Sync Work Span",
            lambda span: do_some_more_work(span, work_response), # Spans can wrap synchronous functions, and they can be nested for fine-grained tracing
            {"attr": "sync work attribute"}
        )

    return await with_active_span(
        tracer,
        "Root Span that does some async work",
        do_some_async_work, # Spans can wrap asynchronous functions
        {"tracing-attr": "Additional attributes can be added to Otel spans by making use of with_active_span like this"}
    )

# This is an example of how to setup queries to be run in parallel
@connector.register_query(parallel_degree=5) # When joining to this function, it will be executed in parallel in batches of 5
async def parallel_query(name: str) -> str:
    await asyncio.sleep(1)
    return f"Hello {name}"

# This is an example of how you can throw an error
# There are different error types including: BadRequest, Forbidden, Conflict, UnprocessableContent, InternalServerError, NotSupported, and BadGateway
@connector.register_query
def error():
    raise UnprocessableContent(message="This is a error", details={"Error": "This is a error!"})

class Foo(BaseModel):
  bar: str = Field(..., description="The bar field") # Add a field description
  baz: Annotated[str, "The baz field"] # A different way to add a field description

# You can use Field or Annotated to add descriptions to the metadata
@connector.register_query
def annotations(foo: Foo | None = Field(..., description="The optional input Foo")) -> Foo | None:
    """Writing a doc-string like this will become the function/procedure description"""
    return None

if __name__ == "__main__":
    start(connector)
