from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class FilterCondition(Base):
    __abstract__ = True

    role_name: Mapped[int] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    condition_type: Mapped[str] = mapped_column(String(50), primary_key=True)  # AND, OR, NOT, FIELD
