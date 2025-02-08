from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class ModelOrderableField(Base):
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    field_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    enable_all_directions: Mapped[bool] = mapped_column(Boolean, default=True)
