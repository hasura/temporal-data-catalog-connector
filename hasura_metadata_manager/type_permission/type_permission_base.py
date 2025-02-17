from enum import Enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class OperationType(Enum):
    QUERY = 'query'
    MUTATION = 'mutation'
    SUBSCRIPTION = 'subscription'


class TypePermission(Base):
    __abstract__ = True

    role_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    type_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    @property
    def name(self):
        return f"{self.role_name}__{self.type_name}"
