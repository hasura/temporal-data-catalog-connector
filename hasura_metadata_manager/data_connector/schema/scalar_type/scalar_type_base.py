# src/hasura_metadata_manager/scalar_type_base.py

import logging

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ....base import Base

logger = logging.getLogger(__name__)


class ScalarType(Base):
    __abstract__ = True
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    representation_name: Mapped[str] = mapped_column(String(50))
    graphql_type_name: Mapped[str] = mapped_column(String(255))

    def __repr__(self):
        return f"<ScalarType(name={self.name}, graphql_type_name={self.graphql_type_name})>"
