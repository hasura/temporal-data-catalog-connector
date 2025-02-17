from typing import Optional, List, Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import literal
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, Session

from ..procedure.procedure_argument import ProcedureArgument
from ..procedure.procedure_base import Procedure as BaseProcedure
from ..type_definition import TypeDefinition
from ...mixins.temporal.temporal_relationship import TemporalRelationship

logger = __import__("logging").getLogger(__name__)

if TYPE_CHECKING:
    from ... import DataConnector


class Procedure(BaseProcedure):
    """Represents a stored procedure."""
    __tablename__ = "procedure"

    # Define the Python-level property
    @hybrid_property
    def pre_check(self):
        return "pre_check"

    # Define the SQL-level expression
    @pre_check.expression
    def pre_check(cls):
        # The `literal` function generates a ClauseElement for SQL
        return literal("pre_check")

    arguments: Mapped[List["ProcedureArgument"]] = TemporalRelationship(
        "ProcedureArgument",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Procedure.name) == ProcedureArgument.procedure_name,
            foreign(Procedure.connector_name) == ProcedureArgument.connector_name,
            foreign(Procedure.subgraph_name) == ProcedureArgument.subgraph_name
        )""",
        info={'skip_constraint': True}
    )
    result_type: Mapped[Optional["TypeDefinition"]] = TemporalRelationship(
        "TypeDefinition",
        primaryjoin=(
            """and_(
                foreign(Procedure.result_type_name) == TypeDefinition.name,     
                foreign(Procedure.result_type_connector_name) == TypeDefinition.connector_name, 
                foreign(Procedure.result_type_subgraph_name) == TypeDefinition.subgraph_name
            )"""
        )
    )
    connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        primaryjoin="""and_(
            foreign(Procedure.connector_name)==DataConnector.name, 
            foreign(Procedure.subgraph_name)==DataConnector.subgraph_name
        )"""
    )

    @classmethod
    def from_json(
            cls: Type["Procedure"],
            json_data: Dict[str, Any],
            connector: "DataConnector",
            session: Session,
    ) -> "Procedure":
        """Create a Procedure from JSON data."""
        logger.debug(f"Creating Procedure: {json_data['name']}")
        procedure = cls(
            name=json_data["name"],
            connector_name=connector.name,
            subgraph_name=connector.subgraph_name,
            description=json_data.get("description"),
        )

        # Set the result type
        result_type_info = json_data.get("result_type")
        result_type_definition = TypeDefinition.from_json({"type": result_type_info}, connector.name,
                                                          connector.subgraph_name, session)
        procedure.result_type_name = result_type_definition.name
        procedure.result_type_connector_name = result_type_definition.connector_name
        procedure.result_type_subgraph_name = result_type_definition.subgraph_name

        session.add(procedure)
        session.flush()



        # Add arguments
        for arg_name, arg_data in json_data.get("arguments", {}).items():
            logger.debug(f"  Adding argument: {arg_name}")
            try:
                ProcedureArgument.from_json(
                    {**arg_data, "name": arg_name, "parent_key": arg_name}, connector, procedure, session
                )
            except Exception as e:
                logger.debug(f"    Error adding argument {arg_name}: {e}")
                raise

        return procedure

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the Procedure to a JSON-compatible dictionary
        that matches the metadata.json structure.
        """
        procedure_dict = {
            "name": self.name
        }

        # Add description only if it exists
        if self.description:
            procedure_dict["description"] = self.description

        # Add result type if it exists
        if self.result_type:
            # Create response type structure
            procedure_dict["result_type"] = {
                "name": self.result_type.name,
                "type": "named"
            }

        # Add arguments
        if self.arguments:
            procedure_dict["arguments"] = {
                arg.name: {
                    "type": arg.type_definition.to_json(),
                    **({"description": arg.description} if arg.description is not None else {})
                } for arg in self.arguments
            }

        return procedure_dict
