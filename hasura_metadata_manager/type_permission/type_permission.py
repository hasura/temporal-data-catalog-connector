from typing import List, Type, Dict, Any

from sqlalchemy.orm import Mapped, validates, Session

from .allowed_field import AllowedField
from .type_permission_base import TypePermission as BaseTypePermission, OperationType
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..object_type.object_type_base import ObjectType
from ..role.role_base import Role
from ..subgraph.subgraph_base import Subgraph


class TypePermission(BaseTypePermission):
    __tablename__ = "type_permission"

    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(TypePermission.subgraph_name)==Subgraph.name)")

    object_type: Mapped["ObjectType"] = TemporalRelationship(
        "ObjectType",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(TypePermission.type_name)==ObjectType.name)"
    )

    role: Mapped["Role"] = TemporalRelationship(
        "Role",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(TypePermission.role_name)==Role.name)"
    )
    allowed_fields: Mapped[List["AllowedField"]] = TemporalRelationship(
        "AllowedField",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(TypePermission.role_name) == AllowedField.role_name, 
            foreign(TypePermission.type_name) == AllowedField.type_name, 
            foreign(TypePermission.subgraph_name) == AllowedField.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    @validates('operation_type')
    def validate_operation_type(self, _key, value):
        if value not in [t.value for t in OperationType]:
            raise ValueError(f"Invalid operation_type: {value}")
        return value

    @classmethod
    def from_json(cls: Type["TypePermission"], json_data: Dict[str, Any], subgraph: "Subgraph",
                  session: Session) -> List["TypePermission"]:
        if json_data.get("kind") != "TypePermissions":
            raise ValueError(f"Expected TypePermissions, got {json_data.get('kind')}")

        def_data = json_data.get("definition", {})
        permissions = def_data.get("permissions", [])

        result = []
        for perm in permissions:
            role_name = perm.get("role")
            if not role_name:
                continue

            # Create permission for each valid operation type
            permission = cls(
                subgraph_name=subgraph.name,
                type_name=def_data["typeName"],
                role_name=role_name
            )
            session.add(permission)
            session.flush()


            # Process allowed fields if present
            allowed_fields = perm.get("output", {}).get("allowedFields", [])
            for field_name in allowed_fields:
                AllowedField.from_json({
                    "fieldName": field_name,
                    "typeName": def_data["typeName"]
                }, permission, session)

            result.append(permission)

        return result

    def to_json(self) -> Dict[str, Any]:
        """
        Convert TypePermission instance to JSON format matching metadata.json structure.

        Returns:
            Dict[str, Any]: JSON representation of type permissions
        """
        # Get all allowed fields for this permission
        field_names = [field.field_name for field in self.allowed_fields]

        return {
            "kind": "TypePermissions",
            "version": "v1",
            "definition": {
                "typeName": self.type_name,
                "permissions": [
                    {
                        "role": self.role_name,
                        "input": None,  # Based on metadata.json format
                        "output": {
                            "allowedFields": field_names
                        }
                    }
                ]
            }
        }
