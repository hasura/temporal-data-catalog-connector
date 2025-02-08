from typing import Optional

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class BooleanExpressionType(Base):
    __abstract__ = True

    # Primary key columns and attributes
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    graphql_type_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_null_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    logical_ops_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    scalar_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self):
        return f"<BooleanExpressionType(name={self.name}, subgraph={self.subgraph_name})>"
