from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class CompatibilityConfig(Base):
    """Represents compatibility configuration"""
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    target_date: Mapped[datetime] = mapped_column(DateTime)

    @property
    def name(self):
        return self.subgraph_name
