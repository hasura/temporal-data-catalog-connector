from typing import Optional, Dict

from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ObjectType(Base):
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    graphql_type_name: Mapped[str] = mapped_column(String(255))
    graphql_input_type_name: Mapped[Optional[str]] = mapped_column(String(255))
    collection_type: Mapped[Optional[str]] = mapped_column(String(255))
    field_mapping: Mapped[Optional[Dict]] = mapped_column(JSON)
