from typing import Dict, Any, List, TYPE_CHECKING, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from . import AggregateExpression


class DataConnectorFunctionMapping(Base):
    """Maps aggregate functions to data connector implementations"""
    __tablename__ = "data_connector_function_mapping"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    data_connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    data_connector_scalar_type: Mapped[str] = mapped_column(String(255), primary_key=True)
    aggregate_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    function_name: Mapped[Optional[str]] = mapped_column(String(255), primary_key=True)
    mapped_function_name: Mapped[Optional[str]] = mapped_column(String(255))

    aggregate_expression: Mapped["AggregateExpression"] = TemporalRelationship(
        "AggregateExpression",
        uselist=False,
        primaryjoin="""and_(
            foreign(DataConnectorFunctionMapping.aggregate_name) == AggregateExpression.name,
            foreign(DataConnectorFunctionMapping.subgraph_name) == AggregateExpression.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls, mapping_data: Dict[str, Any], aggregate: "AggregateExpression", session: Session) -> List[
        "DataConnectorFunctionMapping"]:
        mappings = []
        if mapping_data["functionMapping"]:
            for func_name, func_mapping in mapping_data["functionMapping"].items():
                mapping = cls(
                    aggregate_name=aggregate.name,
                    subgraph_name=aggregate.subgraph_name,
                    data_connector_name=mapping_data["dataConnectorName"],
                    data_connector_scalar_type=mapping_data["dataConnectorScalarType"],
                    function_name=func_name,
                    mapped_function_name=func_mapping["name"]
                )
                mappings.append(mapping)
                session.add(mapping)
                session.flush()
                session.expire_all()
        else:
            mapping = cls(
                aggregate_name=aggregate.name,
                subgraph_name=aggregate.subgraph_name,
                data_connector_name=mapping_data["dataConnectorName"],
                data_connector_scalar_type=mapping_data["dataConnectorScalarType"],
                function_name="",
                mapped_function_name=None)
            mappings.append(mapping)
            session.add(mapping)
            session.flush()
            session.expire_all()

        session.flush()  # Final flush
        return mappings

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the data connector function mapping to its JSON representation.

        The returned JSON structure matches the format expected in the
        dataConnectorAggregationFunctionMapping array elements' functionMapping objects.

        Returns:
            Dict[str, Any]: A dictionary containing the mapped function details with the following structure:
                {
                    "name": str       # The mapped function name in the data connector
                }

        Example output:
            {
                "name": "avg"
            }
        """
        return {
            "name": self.mapped_function_name
        }
