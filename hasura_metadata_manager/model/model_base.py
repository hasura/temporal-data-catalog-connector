from typing import Optional

from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class Model(Base):
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    object_type_name: Mapped[str] = mapped_column(String(255))
    aggregate_expression: Mapped[str] = mapped_column(String(255))
    filter_expression_type: Mapped[str] = mapped_column(String(255))
    global_id_source: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
