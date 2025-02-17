from typing import Type, Dict, Any, TYPE_CHECKING, List

from sqlalchemy.orm import Session, Mapped

from .filter_operation_base import FilterOperation as BaseFilterOperation
from ...mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .filter_operand import FilterOperand
    from .filter_condition import FilterCondition


class FilterOperation(BaseFilterOperation):
    __tablename__ = "filter_operation"

    # Update the relationship to properly back-populate
    condition: Mapped["FilterCondition"] = TemporalRelationship(
        "FilterCondition",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(FilterOperation.role_name) == FilterCondition.role_name, 
            foreign(FilterOperation.subgraph_name) == FilterCondition.subgraph_name, 
            foreign(FilterOperation.model_name) == FilterCondition.model_name, 
            foreign(FilterOperation.condition_type) == FilterCondition.condition_type
        )"""
    )
    operands: Mapped[List["FilterOperand"]] = TemporalRelationship(
        "FilterOperand",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(FilterOperation.role_name) == FilterOperand.role_name,
            foreign(FilterOperation.subgraph_name) == FilterOperand.subgraph_name,
            foreign(FilterOperation.model_name) == FilterOperand.model_name,
            foreign(FilterOperation.condition_type) == FilterOperand.condition_type,
            foreign(FilterOperation.operation_name) == FilterOperand.operation_name
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["FilterOperation"],
                  json_data: Dict[str, Any],
                  condition: "FilterCondition",
                  session: Session) -> "FilterOperation":
        """Create FilterOperation from JSON data"""
        operation = cls(
            role_name=condition.role_name,
            subgraph_name=condition.subgraph_name,
            model_name=condition.model_name,
            condition_type=condition.condition_type,
            operation_name=json_data.get("name"),
            operator=json_data.get("operator", "eq")
        )
        session.add(operation)
        session.flush()
        

        # Process operands
        for position, operand_data in enumerate(json_data.get("operands", [])):
            FilterOperand.from_json(operand_data, operation, position, session)

        return operation

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary"""
        return {
            "name": self.operation_name,
            "operator": self.operator,
            "operands": [operand.to_json() for operand in self.operands]
        }
