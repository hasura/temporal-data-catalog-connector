from typing import TYPE_CHECKING

from .relationship_rdf_mixin import RelationshipRDFMixin

if TYPE_CHECKING:
    pass

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base
from typing import Optional


class RelationshipAggregate(Base, RelationshipRDFMixin):
    __tablename__ = "relationship_aggregate"

    # Primary key columns matching relationship composite key
    relationship_name: Mapped[str] = mapped_column(String, primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String, primary_key=True)
    source_type_name: Mapped[str] = mapped_column(String, primary_key=True)

    # Aggregate specific columns - making aggregate_expression optional
    aggregate_expression: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String)

    def to_dict(self) -> dict:
        return {
            "aggregateExpression": self.aggregate_expression,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict, relationship_name: str, subgraph_name: str,
                  source_type_name: str) -> "RelationshipAggregate":
        return cls(
            relationship_name=relationship_name,
            subgraph_name=subgraph_name,
            source_type_name=source_type_name,
            aggregate_expression=data.get("aggregateExpression"),  # Made optional here too
            description=data.get("description")
        )
