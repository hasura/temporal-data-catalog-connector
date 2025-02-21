from typing import Type, Dict, Any

from sqlalchemy.orm import Session

from .command_permission_preset_base import CommandPermissionPreset as BaseCommandPermissionPreset
from .command_permissions import CommandPermissions


class CommandPermissionPreset(BaseCommandPermissionPreset):
    """Represents argument presets for a CommandPermissions."""
    __tablename__ = "command_permission_preset"

    @classmethod
    def from_json(cls: Type["CommandPermissionPreset"], json_data: Dict[str, Any],
                  permission: CommandPermissions, session: Session) -> "CommandPermissionPreset":
        """Create a CommandPermissionPreset from JSON data."""
        # Extract the argument name and value from the preset data
        # The schema shows this as an array, but we need to determine the exact structure
        # of the preset data to properly parse it
        arg_name = json_data.get("name", "")  # Adjust based on actual structure
        preset_value = json_data.get("value")  # Adjust based on actual structure

        preset = cls(
            subgraph_name=permission.subgraph_name,
            command_name=permission.command_name,
            role=permission.role,
            argument_name=arg_name,
            preset_value_string=str(preset_value) if isinstance(preset_value, str) else None,
            preset_value_number=float(preset_value) if isinstance(preset_value, (int, float)) else None,
            preset_value_boolean=preset_value if isinstance(preset_value, bool) else None
        )
        session.add(preset)
        return preset

    def to_json(self) -> dict:
        """Convert CommandPermissionPreset to JSON representation."""
        # Determine which preset value to use
        if self.preset_value_boolean is not None:
            value = self.preset_value_boolean
        elif self.preset_value_number is not None:
            value = self.preset_value_number
        elif self.preset_value_string is not None:
            value = self.preset_value_string
        else:
            value = None

        return {
            "name": self.argument_name,
            "value": value
        }
