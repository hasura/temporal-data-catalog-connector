from typing import TYPE_CHECKING, Dict, Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from ....base import Base
from ....mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ...schema.collection.collection_uniqueness_constraint import \
        CollectionUniquenessConstraint
    from . import Collection


class UniquenessConstraintColumn(Base):
    """Model to store columns that are part of a uniqueness constraint."""
    __tablename__ = "uniqueness_constraint_column"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    collection_name: Mapped[str] = mapped_column(String(1028), primary_key=True)
    constraint_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    field_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    @property
    def name(self):
        return f"{self.constraint_name}__{self.field_name}"

    constraint: Mapped["CollectionUniquenessConstraint"] = TemporalRelationship(
        "CollectionUniquenessConstraint",
        uselist=False,
        primaryjoin="""and_(
            foreign(UniquenessConstraintColumn.constraint_name) == CollectionUniquenessConstraint.constraint_name, 
            foreign(UniquenessConstraintColumn.collection_name) == CollectionUniquenessConstraint.collection_name, 
            foreign(UniquenessConstraintColumn.connector_name) == CollectionUniquenessConstraint.connector_name, 
            foreign(UniquenessConstraintColumn.subgraph_name) == CollectionUniquenessConstraint.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls, constraint_name: str, field_name: str, collection: "Collection",
                  session: Session) -> "UniquenessConstraintColumn":
        """
        Create a uniqueness constraint column from JSON data.

        Args:
            constraint_name: Name of the parent constraint
            field_name: Name of the field in the constraint
            collection: Parent Collection instance
            session: SQLAlchemy session

        Returns:
            Created UniquenessConstraintColumn instance
        """
        column = cls(
            constraint_name=constraint_name,
            collection_name=collection.name,
            connector_name=collection.connector_name,
            subgraph_name=collection.subgraph_name,
            field_name=field_name
        )
        session.add(column)
        session.flush()


        return column

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the constraint column to a JSON-compatible dictionary.

        Returns:
            Dictionary containing the column configuration
        """
        return {
            "field_name": self.field_name
        }
