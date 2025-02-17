import logging
from typing import Optional, Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from . import AggregateExpression

logger = logging.getLogger(__name__)


class AggregateScalarFunction(Base):
    """Represents a scalar aggregation function"""
    __tablename__ = "aggregate_scalar_function"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    aggregate_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    function_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    return_type: Mapped[str] = mapped_column(String(255))
    aggregated_type: Mapped[Optional[str]] = mapped_column(String(255))

    @property
    def name(self):
        return f"{self.function_name}__{self.aggregated_type}"

    # Relationship back to parent
    aggregate_expression: Mapped["AggregateExpression"] = TemporalRelationship(
        "AggregateExpression",
        uselist=False,
        primaryjoin="""and_(
            foreign(AggregateScalarFunction.aggregate_name) == AggregateExpression.name,
            foreign(AggregateScalarFunction.subgraph_name) == AggregateExpression.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["AggregateScalarFunction"], json_data: Dict[str, Any],
                  aggregated_type: Optional[str],
                  aggregate: "AggregateExpression", session: Session) -> "AggregateScalarFunction":
        """Create an AggregateScalarFunction from JSON data."""
        logger.debug(f"Creating AggregateScalarFunction for aggregate {aggregate.name} "
                     f"with type {aggregated_type}")

        function = cls(
            aggregate_name=aggregate.name,
            subgraph_name=aggregate.subgraph_name,
            function_name=json_data["name"],
            description=json_data.get("description"),
            return_type=json_data["returnType"],
            aggregated_type=aggregated_type
        )
        logger.debug(f"Created AggregateScalarFunction: {function.function_name} "
                     f"returning {function.return_type}")

        session.add(function)
        session.flush()  # Added
        session.expire_all()  # Added
        return function

    def to_json(self) -> Dict[str, Any]:
        """Convert the function to its original JSON structure"""
        logger.debug(f"Starting to_json serialization for aggregate scalar function: {self.name}")
        result = {
            "name": self.function_name,
            "returnType": self.return_type,
            "description": self.description
        }
        logger.debug(f"Completed to_json serialization for {self.name}")
        return result
