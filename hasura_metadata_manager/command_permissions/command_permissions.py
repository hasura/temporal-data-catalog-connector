from typing import List, Dict, Any, Type, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from .command_permissions_base import CommandPermissions as BaseCommandPermissions
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .command_permission_preset import CommandPermissionPreset


class CommandPermissions(BaseCommandPermissions):
    """Main CommandPermission class."""
    __tablename__ = "command_permissions"

    # Relationships
    argument_presets: Mapped[List["CommandPermissionPreset"]] = TemporalRelationship(
        "CommandPermissionPreset",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(CommandPermissions.command_name) == CommandPermissionPreset.command_name,
            foreign(CommandPermissions.subgraph_name) == CommandPermissionPreset.subgraph_name,
            foreign(CommandPermissions.role) == CommandPermissionPreset.role
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["CommandPermissions"], json_data: Dict[str, Any],
                  subgraph_name: str, session: Session) -> List["CommandPermissions"]:
        """Create CommandPermission instances from JSON data."""
        if json_data.get("kind") != "CommandPermissions":
            raise ValueError(f"Expected CommandPermissions, got {json_data.get('kind')}")

        def_data = json_data.get("definition", {})
        command_name = def_data.get("commandName")
        permissions = def_data.get("permissions", [])

        command_permissions = []

        for perm in permissions:
            cmd_perm = cls(
                subgraph_name=subgraph_name,
                command_name=command_name,
                role=perm.get("role"),
                version=json_data.get("version"),
                allow_execution=perm.get("allowExecution", False)
            )
            session.add(cmd_perm)
            session.flush()

            # Create argument presets
            if "argumentPresets" in perm:
                for preset_data in perm.get("argumentPresets", []):
                    CommandPermissionPreset.from_json(
                        preset_data, cmd_perm, session
                    )

            command_permissions.append(cmd_perm)

        return command_permissions

    def to_json(self) -> dict:
        """Convert CommandPermission to JSON representation."""
        # Group all permissions for the same command
        permission_data = {
            "role": self.role,
            "allowExecution": self.allow_execution
        }

        if self.argument_presets:
            permission_data["argumentPresets"] = [
                preset.to_json() for preset in self.argument_presets
            ]

        return {
            "definition": {
                "commandName": self.command_name,
                "permissions": [permission_data]
            },
            "kind": "CommandPermissions",
            "version": self.version
        }
