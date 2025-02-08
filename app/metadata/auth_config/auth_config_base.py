from typing import Optional, Dict

from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class AuthConfig(Base):
    """Represents authentication configuration"""
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    mode_type: Mapped[str] = mapped_column(String(50))  # e.g. "noAuth", "jwt", etc.
    default_role: Mapped[Optional[str]] = mapped_column(String(255))
    session_vars: Mapped[Dict] = mapped_column(JSON)
    version: Mapped[str] = mapped_column(String(50))
