from typing import List, Type, Dict, Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .filter_condition_base import FilterCondition as BaseFilterCondition
from .filter_operation import FilterOperation
from ...mixins.temporal.temporal_relationship import TemporalRelationship
from ...model_permission.model_permission_base import ModelPermission


class FilterCondition(BaseFilterCondition):
    __tablename__ = "filter_condition"

    role_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    condition_type: Mapped[str] = mapped_column(String(50), primary_key=True)  # AND, OR, NOT, FIELD

    # Add the back-reference to ModelPermission
    model_permission: Mapped["ModelPermission"] = TemporalRelationship(
        "ModelPermission",
        uselist=False,
        primaryjoin="""and_(
            foreign(FilterCondition.subgraph_name) == ModelPermission.subgraph_name, 
            foreign(FilterCondition.model_name) == ModelPermission.model_name, 
            foreign(FilterCondition.role_name) == ModelPermission.role_name
        )""",
    )

    operations: Mapped[List["FilterOperation"]] = TemporalRelationship(
        "FilterOperation",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(FilterCondition.subgraph_name) == FilterOperation.subgraph_name, 
            foreign(FilterCondition.model_name) == FilterOperation.model_name, 
            foreign(FilterCondition.role_name) == FilterOperation.role_name, 
            foreign(FilterCondition.condition_type) == FilterOperation.condition_type
        )""",
        info={'skip_constraint': True})

    @classmethod
    def from_json(cls: Type["FilterCondition"],
                  json_data: Dict[str, Any],
                  permission: "ModelPermission",
                  session: Session) -> "FilterCondition":
        """Create FilterCondition from JSON data"""
        condition = cls(
            subgraph_name=permission.subgraph_name,
            model_name=permission.model_name,
            role_name=permission.role_name,
            condition_type=json_data.get("type", "FIELD").upper()
        )
        session.add(condition)
        session.flush()
        


        # Process operations
        if "operations" in json_data:
            for op_data in json_data["operations"]:
                FilterOperation.from_json(op_data, condition, session)
        elif "operation" in json_data:  # Single operation case
            FilterOperation.from_json(json_data["operation"], condition, session)

        return condition

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary"""
        result = {
            "type": self.condition_type.lower()
        }

        if len(self.operations) == 1:
            result["operation"] = self.operations[0].to_json()
        else:
            result["operations"] = [op.to_json() for op in self.operations]

        return result
