from typing import Type, Dict, Any, Union

from sqlalchemy.orm import Mapped, Session

from .filter_operand_base import FilterOperand as BaseFilterOperand
from .filter_operation_base import FilterOperation
from ...mixins.temporal.temporal_relationship import TemporalRelationship


class FilterOperand(BaseFilterOperand):
    """Represents an operand in a filter operation"""
    __tablename__ = "filter_operand"

    operation: Mapped["FilterOperation"] = TemporalRelationship(
        "FilterOperation",
        uselist=False,
        primaryjoin="""and_(
            foreign(FilterOperand.role_name) == FilterOperation.role_name, 
            foreign(FilterOperand.subgraph_name) == FilterOperation.subgraph_name, 
            foreign(FilterOperand.model_name) == FilterOperation.model_name, 
            foreign(FilterOperand.condition_type) == FilterOperation.condition_type, 
            foreign(FilterOperand.operation_name) == FilterOperation.operation_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["FilterOperand"],
                  json_data: Dict[str, Any],
                  operation: "FilterOperation",
                  position: int,
                  session: Session) -> "FilterOperand":
        """Create FilterOperand from JSON data"""
        value_type = json_data.get("type", "value")
        value = json_data.get("value")

        operand = cls(
            role_name=operation.role_name,
            subgraph_name=operation.subgraph_name,
            model_name=operation.model_name,
            condition_type=operation.condition_type,
            operation_name=operation.operation_name,
            operand_position=position,
            field_name=json_data.get("field"),
            value_type=value_type
        )

        # Set the appropriate value field based on type
        if isinstance(value, str):
            operand.string_value = value
        elif isinstance(value, (int, float)):
            operand.number_value = float(value)
        elif isinstance(value, bool):
            operand.boolean_value = value

        session.add(operand)
        session.flush()
        
        return operand

    def to_json(self) -> Dict[str, Union[str, float, bool, str, None]]:
        """Convert to JSON-compatible dictionary"""
        result: Dict[str, Union[str, float, bool, None]] = {
            "type": self.value_type
        }

        if self.field_name:
            result["field"] = self.field_name

        if self.string_value is not None:
            result["value"] = self.string_value
        elif self.number_value is not None:
            result["value"] = self.number_value
        elif self.boolean_value is not None:
            result["value"] = self.boolean_value
        else:
            result["value"] = None

        return result
