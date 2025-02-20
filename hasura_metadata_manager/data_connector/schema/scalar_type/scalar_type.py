from typing import List, Type, Optional, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from ...schema.scalar_type.scalar_type_base import ScalarType as BaseScalarType
from ....boolean_expression_type.boolean_expression_type_operator import BooleanExpressionTypeOperator
from ....mixins.temporal.temporal_relationship import TemporalRelationship
from ....subgraph.subgraph_base import Subgraph

if TYPE_CHECKING:
    pass


# Add relationships that depend on other models
class ScalarType(BaseScalarType):
    __tablename__ = "scalar_type"

    # Relationship to parent Subgraph
    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(ScalarType.subgraph_name) == Subgraph.name)"
    )

    boolean_expression_operators: Mapped[List["BooleanExpressionTypeOperator"]] = TemporalRelationship(
        "BooleanExpressionTypeOperator",
        viewonly=True,
        primaryjoin="""and_(
            foreign(ScalarType.name)==BooleanExpressionTypeOperator.scalar_type_name, 
            foreign(ScalarType.subgraph_name)==BooleanExpressionTypeOperator.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["ScalarType"], json_data: Dict[str, Any], subgraph: "Subgraph",
                  session: Session) -> "ScalarType":
        """Create a ScalarType from JSON data."""
        existing: Optional[ScalarType] = session.query(cls).filter_by(
            name=json_data["definition"]["name"],
            subgraph_name=subgraph.name
        ).first()

        if existing:
            session.add(existing)
            session.flush()
            return existing

        scalar_type = cls(
            name=json_data["definition"]["name"],
            subgraph_name=subgraph.name,
            representation_name=json_data.get("representation", {}).get("type", "string"),
            graphql_type_name=json_data["definition"]["graphql"]["typeName"]
        )
        session.add(scalar_type)
        session.flush()

        return scalar_type

    def to_json(self) -> Dict[str, Any]:
        """Convert the scalar type to a JSON-compatible dictionary"""
        return {
            "kind": "ScalarType",
            "version": "v1",
            "definition": {
                "name": self.name,
                "graphql": {
                    "typeName": self.graphql_type_name
                },
                "description": None
            }
        }
