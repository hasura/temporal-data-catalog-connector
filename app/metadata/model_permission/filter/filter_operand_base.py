from typing import Optional

from sqlalchemy import Integer, String, Text, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class FilterOperand(Base):
    """Represents an operand in a filter operation"""
    __abstract__ = True

    role_name: Mapped[int] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[int] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[int] = mapped_column(String(255), primary_key=True)
    condition_type: Mapped[int] = mapped_column(String(255), primary_key=True)
    operation_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    operator: Mapped[str] = mapped_column(String(50), primary_key=True)  # eq, gt, lt, etc.
    operand_position: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_name: Mapped[str] = mapped_column(String(255))
    value_type: Mapped[str] = mapped_column(String(50))  # field, value, variable
    string_value: Mapped[Optional[str]] = mapped_column(Text)
    number_value: Mapped[Optional[float]] = mapped_column(Numeric)
    boolean_value: Mapped[Optional[bool]] = mapped_column(Boolean)
