from typing import Optional

from sqlalchemy import String, Text, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class Command(Base):
    """Main Command class representing the command definition."""
    __abstract__ = True

    # Primary key fields
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Basic fields
    version: Mapped[str] = mapped_column(String(10))  # v1 or v2
    description: Mapped[Optional[str]] = mapped_column(Text)
    output_type: Mapped[str] = mapped_column(String(255))
    connector_name: Mapped[str] = mapped_column(String(255))

    # GraphQL specific fields
    graphql_deprecated: Mapped[Optional[bool]] = mapped_column(Boolean)
    graphql_root_field_kind: Mapped[str] = mapped_column(
        Enum("Query", "Mutation", name="root_field_kind")
    )
    graphql_root_field_name: Mapped[str] = mapped_column(String(255))

