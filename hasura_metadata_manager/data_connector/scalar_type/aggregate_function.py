import logging
from typing import Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from ...base import Base
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .. import DataConnector
    from ..type_definition import TypeDefinition

logger = logging.getLogger(__name__)


class AggregateFunction(Base):
    __tablename__ = "aggregate_function"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    scalar_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    function_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    return_type_name: Mapped[str] = mapped_column(String(255))
    return_type_subgraph_name: Mapped[str] = mapped_column(String(255))
    return_type_connector_name: Mapped[str] = mapped_column(String(255))

    @property
    def name(self):
        return f"{self.function_name}__{self.scalar_type_name}"

    result_type = TemporalRelationship(
        'TypeDefinition',
        primaryjoin="""and_(
            foreign(AggregateFunction.return_type_name)==TypeDefinition.name, 
            foreign(AggregateFunction.return_type_subgraph_name)==TypeDefinition.subgraph_name, 
            foreign(AggregateFunction.return_type_connector_name)==TypeDefinition.connector_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["AggregateFunction"],
                  scalar_type_name: str,
                  function_name: str,
                  function_data: Dict[str, Any],
                  connector: "DataConnector",
                  session: Session) -> "AggregateFunction":
        from ..type_definition import TypeDefinition

        return_type = TypeDefinition.from_json({"type": function_data.get("result_type", {})},
                                               connector.name, connector.subgraph_name, session)

        agg_function = cls(
            return_type_name=return_type.name,
            return_type_connector_name=return_type.connector_name,
            return_type_subgraph_name=return_type.subgraph_name,
            connector_name=connector.name,
            subgraph_name=connector.subgraph_name,
            function_name=function_name,
            scalar_type_name=scalar_type_name
        )
        session.add(agg_function)
        session.flush()


        return agg_function

    def to_json(self) -> Dict[str, Any]:
        return {
            # "name": self.function_name,
            "result_type": self.result_type.to_json() if self.result_type else None
        }
