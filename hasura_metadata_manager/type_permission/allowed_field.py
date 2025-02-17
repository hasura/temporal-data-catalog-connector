from typing import Type, Dict, Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .type_permission_base import TypePermission
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..object_type.field import ObjectField


class AllowedField(Base):
    __tablename__ = "allowed_field"

    role_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    type_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    field_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    object_type_name: Mapped[str] = mapped_column(String(255))

    @property
    def name(self):
        return f"{self.role_name}__{self.object_type_name}__{self.field_name}"

    type_permission: Mapped["TypePermission"] = TemporalRelationship(
        "TypePermission",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(AllowedField.role_name) == TypePermission.role_name,
            foreign(AllowedField.subgraph_name) == TypePermission.subgraph_name, 
            foreign(AllowedField.type_name) == TypePermission.type_name
        )"""
    )
    object_field: Mapped["ObjectField"] = TemporalRelationship(
        "ObjectField",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(AllowedField.subgraph_name) == ObjectField.subgraph_name,
            foreign(AllowedField.object_type_name) == ObjectField.object_type_name,
            foreign(AllowedField.field_name) == ObjectField.logical_field_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["AllowedField"], json_data: Dict[str, Any],
                  type_permission: "TypePermission", session: Session) -> "AllowedField":
        field = cls(
            subgraph_name=type_permission.subgraph_name,
            type_name=type_permission.type_name,
            role_name=type_permission.role_name,
            field_name=json_data["fieldName"],
            object_type_name=json_data["typeName"]
        )
        session.add(field)
        session.flush()
        
        return field

    def allowed_field_to_json(self) -> Dict[str, Any]:
        """
        Convert AllowedField instance to JSON format.
        This is typically used as part of TypePermission's to_json method.

        Returns:
            Dict[str, Any]: JSON representation of allowed field
        """
        return {
            "fieldName": self.field_name,
            "typeName": self.object_type_name
        }
