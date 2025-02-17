from typing import Optional

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class ObjectField(Base):
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    object_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    logical_field_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    scalar_type_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_nullable: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False)
    deprecation_reason: Mapped[Optional[str]] = mapped_column(Text)
    default_value: Mapped[Optional[str]] = mapped_column(Text)
    is_array: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def name(self) -> str:
        return self.logical_field_name
