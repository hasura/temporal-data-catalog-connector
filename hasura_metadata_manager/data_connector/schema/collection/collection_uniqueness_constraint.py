from typing import List, Dict, Any, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from ...schema.collection.uniqueness_constraint_column import UniquenessConstraintColumn
from ....base import Base
from ....mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from . import Collection


class CollectionUniquenessConstraint(Base):
    """Model to store collection uniqueness constraints."""
    __tablename__ = "collection_uniqueness_constraint"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    collection_name: Mapped[str] = mapped_column(String(1028), primary_key=True)
    constraint_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    @property
    def name(self):
        return self.constraint_name

    collection: Mapped["Collection"] = TemporalRelationship(
        "Collection",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(CollectionUniquenessConstraint.collection_name) == Collection.name, 
            foreign(CollectionUniquenessConstraint.connector_name) == Collection.connector_name, 
            foreign(CollectionUniquenessConstraint.subgraph_name) == Collection.subgraph_name
        )"""
    )
    columns: Mapped[List["UniquenessConstraintColumn"]] = TemporalRelationship(
        "UniquenessConstraintColumn",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(UniquenessConstraintColumn.constraint_name) == CollectionUniquenessConstraint.constraint_name, 
            foreign(UniquenessConstraintColumn.collection_name) == CollectionUniquenessConstraint.collection_name, 
            foreign(UniquenessConstraintColumn.connector_name) == CollectionUniquenessConstraint.connector_name, 
            foreign(UniquenessConstraintColumn.subgraph_name) == CollectionUniquenessConstraint.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls, constraint_name: str, constraint_data: Dict[str, Any],
                  collection: "Collection", session: Session) -> "CollectionUniquenessConstraint":
        """
        Create a uniqueness constraint from JSON data.

        Args:
            constraint_name: Name of the constraint
            constraint_data: Dictionary containing constraint configuration
            collection: Parent Collection instance
            session: SQLAlchemy session

        Returns:
            Created CollectionUniquenessConstraint instance
        """
        constraint = cls(
            constraint_name=constraint_name,
            collection_name=collection.name,
            connector_name=collection.connector_name,
            subgraph_name=collection.subgraph_name
        )
        session.add(constraint)
        session.flush()



        # Create constraint columns
        for column_name in constraint_data.get("unique_columns", []):
            column = UniquenessConstraintColumn.from_json(
                constraint_name=constraint_name,
                field_name=column_name,
                collection=collection,
                session=session
            )
            constraint.columns.append(column)

        return constraint

    def to_json(self) -> Dict[str, Any]:
        """Convert the constraint to a JSON-compatible dictionary."""
        return {
            "unique_columns": [column.field_name for column in self.columns]
        }
