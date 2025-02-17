from typing import Dict

from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class LifecyclePluginHook(Base):
    """Represents a lifecycle plugin hook configuration"""
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    url: Mapped[str] = mapped_column(String(1024))
    pre_hook: Mapped[bool] = mapped_column(Boolean)
    config: Mapped[Dict] = mapped_column(JSON)
    version: Mapped[str] = mapped_column(String(50))
