from typing import Dict

from sqlalchemy import String, JSON, CheckConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ..type_permission import OperationType


class GraphQLConfig(Base):
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[Dict] = mapped_column(JSON)
    operation_type: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint(f"operation_type IN {tuple(t.value for t in OperationType)}")
    )
    root_operation_type_name: Mapped[str] = mapped_column(String(255))
    apollo_federation_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
