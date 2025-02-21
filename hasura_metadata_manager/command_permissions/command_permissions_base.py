from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class CommandPermissions(Base):
    """Main CommandPermission class."""
    __abstract__ = True

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    command_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    role: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Basic fields
    version: Mapped[str] = mapped_column(String(10))  # v1 or v2
    allow_execution: Mapped[bool] = mapped_column(Boolean, default=False)



