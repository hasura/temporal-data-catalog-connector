from typing import List, Type, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from ..function.function_argument import FunctionArgument
from ..function.function_base import Function as BaseFunction
from ..schema.scalar_type import ScalarType
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..data_connector_base import DataConnector


class Function(BaseFunction):
    __tablename__ = "function"

    connector: Mapped["DataConnector"] = TemporalRelationship(
        "DataConnector",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Function.connector_name)==DataConnector.name, 
            foreign(Function.subgraph_name)==DataConnector.subgraph_name
        )"""
    )
    return_type: Mapped["ScalarType"] = TemporalRelationship(
        "ScalarType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Function.return_type_name)==ScalarType.name, 
            foreign(Function.subgraph_name)==ScalarType.subgraph_name
        )"""
    )
    arguments: Mapped[List["FunctionArgument"]] = TemporalRelationship(
        "FunctionArgument",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(FunctionArgument.function_name)==Function.name,
            foreign(FunctionArgument.connector_name)==Function.connector_name,
            foreign(FunctionArgument.subgraph_name)==Function.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["Function"], json_data: Dict[str, Any], connector: "DataConnector",
                  session: Session) -> "Function":
        """Create a Function entity from JSON data."""
        return_type_info = json_data.get("return_type", {})
        if isinstance(return_type_info, dict):
            return_type_name = return_type_info.get("name")
        else:
            return_type_name = return_type_info

        function = cls(
            name=json_data.get("name"),
            connector_name=connector.name,
            subgraph_name=connector.subgraph_name,
            description=json_data.get("description"),
            return_type_name=return_type_name,
            return_type_connector=connector.name
        )

        session.add(function)
        session.flush()


        if "arguments" in json_data:
            for arg_data in json_data["arguments"]:
                FunctionArgument.from_json(arg_data, function, session)

        return function

    def to_json(self) -> Dict[str, Any]:
        pass
