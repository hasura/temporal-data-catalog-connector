from typing import Type, Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..base import Base
from .command_base import Command


class CommandSourceMapping(Base):
    """Represents argument mappings for a Command's source."""
    __tablename__ = "command_source_mapping"

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    command_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_key: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Value field
    target_value: Mapped[str] = mapped_column(Text)

    @classmethod
    def from_json(cls: Type["CommandSourceMapping"], source_key: str,
                  target_value: Any, command: Command, session: Session) -> "CommandSourceMapping":
        """Create a CommandSourceMapping from key-value pair."""
        mapping = cls(
            subgraph_name=command.subgraph_name,
            command_name=command.name,
            source_key=source_key,
            target_value=str(target_value)  # Convert any value to string for storage
        )
        session.add(mapping)
        return mapping
