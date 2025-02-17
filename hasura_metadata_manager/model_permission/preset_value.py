from typing import Optional, Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import String, Integer, Text, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..data_connector.schema.scalar_type.scalar_type import ScalarType
    from .model_argument_preset import ModelArgumentPreset


class PresetValue(Base):
    """Represents a typed value for a model argument preset"""
    __tablename__ = "preset_value"

    role_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    argument_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    value_position: Mapped[int] = mapped_column(Integer, primary_key=True)
    scalar_type_name: Mapped[str] = mapped_column(String(255))
    string_value: Mapped[Optional[str]] = mapped_column(Text)
    number_value: Mapped[Optional[float]] = mapped_column(Numeric)
    boolean_value: Mapped[Optional[bool]] = mapped_column(Boolean)

    argument_preset: Mapped["ModelArgumentPreset"] = TemporalRelationship(
        "ModelArgumentPreset",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(PresetValue.subgraph_name) == ModelArgumentPreset.subgraph_name, 
            foreign(PresetValue.model_name) == ModelArgumentPreset.model_name, 
            foreign(PresetValue.role_name) == ModelArgumentPreset.role_name, 
            foreign(PresetValue.argument_name) == ModelArgumentPreset.argument_name
        )"""
    )
    scalar_type: Mapped["ScalarType"] = TemporalRelationship(
        "ScalarType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(PresetValue.subgraph_name) == ScalarType.subgraph_name, 
            foreign(PresetValue.scalar_type_name) == ScalarType.name
        )"""
    )

    @classmethod
    def from_json(cls: Type["PresetValue"],
                  json_data: Dict[str, Any],
                  preset: "ModelArgumentPreset",
                  session: Session) -> "PresetValue":
        """Create PresetValue from JSON data"""
        value_type = json_data.get("type", "string")
        value = json_data.get("value")

        preset_value = cls(
            subgraph_name=preset.subgraph_name,
            model_name=preset.model_name,
            role_name=preset.role_name,
            argument_name=preset.argument_name,
            value_position=json_data.get("position", 0),
            scalar_type_name=value_type
        )

        # Set the appropriate value field based on type
        if value_type == "string":
            preset_value.string_value = str(value)
        elif value_type in ["int32", "int64", "float64"]:
            preset_value.number_value = float(value)
        elif value_type == "boolean":
            preset_value.boolean_value = bool(value)

        session.add(preset_value)
        session.flush()
        
        return preset_value

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary"""
        if self.string_value is not None:
            value = self.string_value
        elif self.number_value is not None:
            value = self.number_value
        elif self.boolean_value is not None:
            value = self.boolean_value
        else:
            value = None

        return {
            "type": self.scalar_type_name,
            "value": value,
            "position": self.value_position
        }
