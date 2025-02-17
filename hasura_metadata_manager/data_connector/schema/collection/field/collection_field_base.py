from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .....base import Base


class CollectionField(Base):
    __abstract__ = True

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=True)
    collection_name: Mapped[str] = mapped_column(String(1028), primary_key=True, nullable=True)
    physical_field_name: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=True)

    # Type definition reference
    type_definition_subgraph_name: Mapped[str] = mapped_column(String(255))
    type_definition_connector_name: Mapped[str] = mapped_column(String(255))
    type_definition_name: Mapped[str] = mapped_column(String(255))

    # Metadata fields
    description: Mapped[Optional[str]] = mapped_column(String(1023))  # Increased length

    @property
    def name(self):
        return self.physical_field_name
