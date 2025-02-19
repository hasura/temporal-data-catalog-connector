from typing import Optional, Type, Dict, Any, TYPE_CHECKING

from sqlalchemy import String, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..base import Base
from .command_base import Command

if TYPE_CHECKING:
    pass

class CommandArgument(Base):
    """Represents arguments for a Command."""
    __tablename__ = "command_argument"

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    command_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Basic fields
    type: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    default_value_string: Mapped[Optional[str]] = mapped_column(Text)
    default_value_number: Mapped[Optional[float]] = mapped_column(Float)
    default_value_boolean: Mapped[Optional[bool]] = mapped_column(Boolean)

    @classmethod
    def from_json(cls: Type["CommandArgument"], json_data: Dict[str, Any],
                  command: Command, session: Session) -> "CommandArgument":
        """Create a CommandArgument from JSON data."""
        default_value = json_data.get("defaultValue")

        arg = cls(
            subgraph_name=command.subgraph_name,
            command_name=command.name,
            name=json_data.get("name"),
            type=json_data.get("type"),
            description=json_data.get("description"),
            default_value_string=str(default_value) if isinstance(default_value, str) else None,
            default_value_number=float(default_value) if isinstance(default_value, (int, float)) else None,
            default_value_boolean=default_value if isinstance(default_value, bool) else None
        )
        session.add(arg)
        return arg

    def to_json(self) -> dict:
        """Convert CommandArgument to JSON representation."""
        # Determine which default value to use
        if self.default_value_boolean is not None:
            default_value = self.default_value_boolean
        elif self.default_value_number is not None:
            default_value = self.default_value_number
        elif self.default_value_string is not None:
            default_value = self.default_value_string
        else:
            default_value = None

        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "defaultValue": default_value
        }
