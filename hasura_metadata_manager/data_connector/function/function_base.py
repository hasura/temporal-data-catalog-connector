from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class Function(Base):
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    return_type_name: Mapped[str] = mapped_column(String(255))
    return_type_type: Mapped[str] = mapped_column(String(255))
    return_type_connector: Mapped[str] = mapped_column(String(255))
