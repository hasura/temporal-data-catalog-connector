from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class FieldMap(Base):
    """Base class for FieldMap that defines the schema and attributes."""
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    object_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    logical_field_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    collection_name: Mapped[str] = mapped_column(String(1028), primary_key=True)
    physical_field_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    @property
    def name(self) -> str:
        return self.logical_field_name + " <- " + self.physical_field_name
