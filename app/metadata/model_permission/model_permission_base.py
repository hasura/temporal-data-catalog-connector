from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ModelPermission(Base):
    __abstract__ = True

    role_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    allow_subscriptions: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def name(self):
        return f"{self.role_name}__{self.model_name}"
