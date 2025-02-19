# src/hasura_metadata_manager/aggregate_expression_base.py
from typing import Optional

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class AggregateExpression(Base):
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    count_enabled: Mapped[bool] = mapped_column(Boolean)
    count_description: Mapped[Optional[str]] = mapped_column(Text)
    count_return_type: Mapped[Optional[str]] = mapped_column(String(255))
    count_distinct_enabled: Mapped[Optional[bool]] = mapped_column(Boolean)
    count_distinct_description: Mapped[Optional[str]] = mapped_column(Text)
    count_distinct_return_type: Mapped[Optional[str]] = mapped_column(String(255))
    graphql_select_type_name: Mapped[str] = mapped_column(String(255))
    graphql_deprecated: Mapped[Optional[bool]] = mapped_column(Boolean)
    operand_object_aggregate_type: Mapped[Optional[str]] = mapped_column(String(255))
    operand_scalar_type: Mapped[Optional[str]] = mapped_column(String(255))  # New field
