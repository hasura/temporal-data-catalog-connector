from enum import Enum
from typing import Optional

from sqlalchemy import String, Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, validates

from ...base import Base


class TypeDefinitionKind(str, Enum):
    NAMED = "named"
    ARRAY = "array"
    NULLABLE = "nullable"
    PREDICATE = "predicate"


class TypeDefinition(Base):
    """
    Base class for TypeDefinition with natural key attributes
    """
    __abstract__ = True

    # Natural key columns
    subgraph_name: Mapped[Optional[str]] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[TypeDefinitionKind] = mapped_column(SQLAlchemyEnum(TypeDefinitionKind))

    # if array or nullable -> point to child
    child_type_name: Mapped[Optional[str]] = mapped_column(String(255))

    # generated name
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # if named - classify as scalar or collection
    scalar_type_name: Mapped[Optional[str]] = mapped_column(String(255))
    collection_type_name: Mapped[Optional[str]] = mapped_column(String(255))

    @validates('type')
    def validate_type(self, _key, value):
        if isinstance(value, TypeDefinitionKind):
            return value
        if isinstance(value, str):
            try:
                return TypeDefinitionKind(value)
            except ValueError:
                raise ValueError(
                    f"Invalid type value: {value}. Must be one of: {[t.value for t in TypeDefinitionKind]}")
        raise ValueError(f"Type must be string or TypeDefinitionKind, got {type(value)}")
