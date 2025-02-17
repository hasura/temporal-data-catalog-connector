import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..type_definition.type_definition import TypeDefinition
from ...base import Base
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..procedure import Procedure
    from ... import DataConnector

logger = logging.getLogger(__name__)


class ProcedureArgument(Base):
    """
    Represents an argument in a procedure definition.

    Each argument has:
    - A composite primary key (procedure_name, name, connector_name, subgraph_name)
    - A type definition (with optional scalar or collection reference)
    - An argument type (SCALAR, COLLECTION, or PREDICATE)
    - Optional description and required flag
    """
    __tablename__ = "procedure_argument"

    # Composite primary key
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    procedure_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Type definition natural key columns
    type_definition_connector_name: Mapped[str] = mapped_column(String(255))
    type_definition_name: Mapped[str] = mapped_column(String(255))
    type_definition_subgraph_name: Mapped[str] = mapped_column(String(255))

    # Type definition relationship using natural key
    type_definition: Mapped[TypeDefinition] = TemporalRelationship(
        "TypeDefinition",
        primaryjoin="""and_(
            foreign(ProcedureArgument.type_definition_connector_name) == TypeDefinition.connector_name,
            foreign(ProcedureArgument.type_definition_name) == TypeDefinition.name,
            foreign(ProcedureArgument.type_definition_subgraph_name) == TypeDefinition.subgraph_name
        )"""
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(String(1023))

    # Relationships
    procedure: Mapped["Procedure"] = TemporalRelationship(
        "Procedure",
        primaryjoin="""and_(
            foreign(ProcedureArgument.procedure_name) == Procedure.name, 
            foreign(ProcedureArgument.connector_name) == Procedure.connector_name, 
            foreign(ProcedureArgument.subgraph_name) == Procedure.subgraph_name,
            foreign(ProcedureArgument.name) == Procedure.pre_check 
        )"""
    )

    @classmethod
    def from_json(cls,
                  json_data: Dict[str, Any],
                  connector: "DataConnector",
                  procedure: "Procedure",
                  session: Session) -> "ProcedureArgument":
        """
        Create a ProcedureArgument from JSON data.

        Args:
            json_data: Dictionary containing argument definition
            connector: Parent DataConnector instance
            procedure: Parent Procedure instance
            session: SQLAlchemy session

        Returns:
            Created ProcedureArgument instance
        """
        logger.debug(f"Creating argument {json_data.get('name')} for procedure {procedure.name}")

        type_info = json_data["type"]

        # Create type definition
        type_definition = TypeDefinition.from_json({"type": type_info}, connector.name, connector.subgraph_name,
                                                   session)

        # Create and return the argument
        argument = cls(
            procedure_name=procedure.name,
            name=json_data["name"],
            type_definition_connector_name=type_definition.connector_name,
            type_definition_name=type_definition.name,
            type_definition_subgraph_name=type_definition.subgraph_name,
            connector_name=procedure.connector_name,
            subgraph_name=procedure.subgraph_name,
            description=json_data.get("description")
        )

        session.add(argument)
        session.flush()


        logger.debug(f"Created argument {argument.name} for procedure {procedure.name}")
        return argument

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the ProcedureArgument to a JSON-compatible dictionary

        Returns:
            Dictionary containing the argument definition
        """
        result = {
            "name": self.name,
            "type": self.type_definition.to_json()
        }

        if self.description:
            result["description"] = self.description

        return result

    def __repr__(self) -> str:
        """String representation of the ProcedureArgument"""
        return (f"ProcedureArgument(name='{self.name}', "
                f"procedure='{self.procedure_name}', "
                f"type={self.type_definition})")
