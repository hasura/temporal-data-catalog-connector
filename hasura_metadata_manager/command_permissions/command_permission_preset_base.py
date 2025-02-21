from typing import Optional

from sqlalchemy import String, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column

from hasura_metadata_manager.base import Base


class CommandPermissionPreset(Base):
    """Represents argument presets for a CommandPermissions."""
    __abstract__ = True

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    command_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    role: Mapped[str] = mapped_column(String(255), primary_key=True)
    argument_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Separate columns for different value types to maintain normalization
    preset_value_string: Mapped[Optional[str]] = mapped_column(String(255))
    preset_value_number: Mapped[Optional[float]] = mapped_column(Float)
    preset_value_boolean: Mapped[Optional[bool]] = mapped_column(Boolean)


