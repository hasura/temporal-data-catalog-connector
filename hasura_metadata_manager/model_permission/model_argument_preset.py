from typing import List, Type, Dict, Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .model_permission_base import ModelPermission
from .preset_value import PresetValue
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship


class ModelArgumentPreset(Base):
    """Represents preset arguments for model permissions"""
    __tablename__ = "model_argument_preset"

    role_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    argument_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    model_permission: Mapped["ModelPermission"] = TemporalRelationship(
        "ModelPermission",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelArgumentPreset.subgraph_name) == ModelPermission.subgraph_name, 
            foreign(ModelArgumentPreset.model_name) == ModelPermission.model_name, 
            foreign(ModelArgumentPreset.role_name) == ModelPermission.role_name
        )""",
    )
    values: Mapped[List["PresetValue"]] = TemporalRelationship(
        "PresetValue",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelArgumentPreset.role_name) == PresetValue.role_name,
            foreign(ModelArgumentPreset.subgraph_name) == PresetValue.subgraph_name,
            foreign(ModelArgumentPreset.model_name) == PresetValue.model_name,
            foreign(ModelArgumentPreset.argument_name) == PresetValue.argument_name,
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["ModelArgumentPreset"],
                  json_data: Dict[str, Any],
                  permission: "ModelPermission",
                  session: Session) -> "ModelArgumentPreset":
        """Create ModelArgumentPreset from JSON data"""
        preset = cls(
            subgraph_name=permission.subgraph_name,
            model_name=permission.model_name,
            role_name=permission.role_name,
            argument_name=json_data.get("argument")
        )
        session.add(preset)
        session.flush()
        


        # Process preset values
        for value_data in json_data.get("values", []):
            PresetValue.from_json(value_data, preset, session)

        return preset

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary"""
        return {
            "argument": self.argument_name,
            "values": [value.to_json() for value in self.values]
        }
