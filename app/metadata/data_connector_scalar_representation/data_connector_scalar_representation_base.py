from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class DataConnectorScalarRepresentation(Base):
    __abstract__ = True

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    data_connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Physical scalar type from the data connector
    data_connector_scalar_type: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Logical scalar type name
    scalar_type_name: Mapped[str] = mapped_column(String(50))

    # Optional GraphQL-related information
    graphql_comparison_expression_type_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    @property
    def name(self) -> str:
        return self.scalar_type_name
