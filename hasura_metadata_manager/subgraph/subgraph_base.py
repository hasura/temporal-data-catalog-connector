from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class Subgraph(Base):
    __abstract__ = True

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
