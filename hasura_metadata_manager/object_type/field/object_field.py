from typing import Type, Dict, Any

from sqlalchemy.orm import Mapped, Session

from .object_field_base import ObjectField as BaseObjectField
from ...data_connector.schema.scalar_type.scalar_type_base import ScalarType
from ...mixins.temporal.temporal_relationship import TemporalRelationship
from ...object_type.object_type_base import ObjectType


class ObjectField(BaseObjectField):
    __tablename__ = "object_field"

    object_type: Mapped["ObjectType"] = TemporalRelationship(
        "ObjectType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ObjectField.object_type_name) == ObjectType.name,
            foreign(ObjectField.subgraph_name) == ObjectType.subgraph_name
        )"""
    )
    scalar_type: Mapped["ScalarType"] = TemporalRelationship(
        "ScalarType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ObjectField.scalar_type_name) == ScalarType.name,
            foreign(ObjectField.subgraph_name) == ScalarType.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["ObjectField"], json_data: Dict[str, Any], object_type: "ObjectType",
                  session: Session) -> "ObjectField":
        type_info = json_data.get("type", {})

        # Handle both string and dictionary type specifications
        if isinstance(type_info, str):
            scalar_type_name = type_info
            is_array = scalar_type_name.startswith('[') and scalar_type_name.endswith(']')
            scalar_type_name = scalar_type_name.replace('[', '').replace(']', '')
            scalar_type_name = scalar_type_name.rstrip('!')
            is_nullable = not type_info.endswith('!')
        else:
            scalar_type_name = type_info.get("name", "String")
            is_nullable = not type_info.get("required", False)
            is_array = type_info.get("isArray", False)

        field = cls(
            object_type_name=object_type.name,
            logical_field_name=json_data["name"],
            scalar_type_name=scalar_type_name,
            subgraph_name=object_type.subgraph_name,
            description=json_data.get("description"),
            is_nullable=is_nullable,
            is_array=is_array,  # Add this field
            is_deprecated=json_data.get("deprecated", False),
            deprecation_reason=json_data.get("deprecationReason"),
            default_value=json_data.get("defaultValue")
        )
        session.add(field)
        session.flush()

        return field

    def to_json(self) -> dict:
        """Convert ObjectField to JSON representation matching hasura_metadata_manager format."""
        type_name = self.scalar_type_name
        if self.is_array:
            type_name = f"[{type_name}]"
        if not self.is_nullable:
            type_name = f"{type_name}!"

        return {
            "arguments": [],  # Fields don't have arguments in current implementation
            "deprecated": self.is_deprecated if self.is_deprecated else None,
            "description": self.description,
            "name": self.logical_field_name,
            "type": type_name
        }
