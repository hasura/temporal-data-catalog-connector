import logging
from typing import Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..schema.scalar_type import ScalarType
from ...base import Base
from ...mixins.temporal.temporal_relationship import TemporalRelationship

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..function.function import Function


class FunctionArgument(Base):
    """Represents an argument for a function"""
    __tablename__ = "function_argument"

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    function_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Type information
    scalar_type_name: Mapped[str] = mapped_column(String(255))
    scalar_type_type: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1023), nullable=True)
    is_required: Mapped[bool] = mapped_column(default=False)

    function: Mapped["Function"] = TemporalRelationship(
        "Function",
        viewonly=True,
        primaryjoin="""and_(
            foreign(FunctionArgument.function_name) == Function.name,
            foreign(FunctionArgument.connector_name) == Function.connector_name,
            foreign(FunctionArgument.subgraph_name) == Function.subgraph_name
        )"""
    )

    scalar_type: Mapped["ScalarType"] = TemporalRelationship(
        "ScalarType",
        viewonly=True,
        primaryjoin="""and_(
            foreign(FunctionArgument.scalar_type_name) == ScalarType.name,
            foreign(FunctionArgument.subgraph_name) == ScalarType.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["FunctionArgument"],
                  json_data: Dict[str, Any],
                  function: "Function",
                  session: Session) -> "FunctionArgument":
        """Create a FunctionArgument from JSON data."""
        type_info = json_data.get("type", {}).get('name')

        argument = cls(
            function_name=function.name,
            connector_name=function.connector_name,
            subgraph_name=function.subgraph_name,
            name=json_data["name"],
            scalar_type_name=type_info.rstrip('!'),
            scalar_type_type=json_data.get("type", {}).get('type'),
            description=json_data.get("description"),
            is_required=type_info.endswith('!')
        )

        session.add(argument)
        session.flush()

        return argument

    def to_json(self) -> Dict[str, Any]:
        return {
            'type': {
                'name': self.scalar_type_name,
                'type': self.scalar_type_type
            }
        }

    def __repr__(self) -> str:
        """String representation of the FunctionArgument"""
        return (f"<FunctionArgument(name='{self.name}', "
                f"function='{self.function_name}', "
                f"type='{self.scalar_type_name}')>")
