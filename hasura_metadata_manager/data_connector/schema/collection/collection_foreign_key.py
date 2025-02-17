from itertools import groupby
from operator import attrgetter
from typing import TYPE_CHECKING, Dict, Any, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from ....base import Base
from ....mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from . import Collection


class CollectionForeignKey(Base):
    __tablename__ = "collection_foreign_key"

    fk_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    collection_name: Mapped[str] = mapped_column(String(1028), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    field_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    target_collection: Mapped[str] = mapped_column(String(255))
    target_field: Mapped[str] = mapped_column(String(255))

    @property
    def name(self):
        return self.fk_name

    collection: Mapped["Collection"] = TemporalRelationship(
        "Collection",
        primaryjoin="""and_(
            foreign(CollectionForeignKey.collection_name) == Collection.name, 
            foreign(CollectionForeignKey.connector_name) == Collection.connector_name, 
            foreign(CollectionForeignKey.subgraph_name) == Collection.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls, fk_name: str, fk_data: Dict[str, Any],
                  collection: "Collection", session: Session) -> List["CollectionForeignKey"]:
        """
        Create foreign keys from JSON data.

        Args:
            fk_name: Name of the foreign key
            fk_data: Dictionary containing foreign key configuration
            collection: Parent Collection instance
            session: SQLAlchemy session

        Returns:
            List of created CollectionForeignKey instances
        """
        foreign_keys = []
        for source_field, target_field in fk_data.get("column_mapping", {}).items():
            fk = cls(
                fk_name=fk_name,
                collection_name=collection.name,
                connector_name=collection.connector_name,
                subgraph_name=collection.subgraph_name,
                field_name=source_field,
                target_collection=fk_data["foreign_collection"],
                target_field=target_field
            )
            session.add(fk)
            session.flush()


            foreign_keys.append(fk)

        return foreign_keys

    @classmethod
    def serialize_foreign_keys(cls, foreign_keys: List["CollectionForeignKey"]) -> Dict[str, Any]:
        """
        Serialize a list of foreign keys, grouping them by fk_name.

        Args:
            foreign_keys: List of CollectionForeignKey instances

        Returns:
            Dictionary of serialized foreign keys grouped by fk_name
        """
        result = {}
        # Sort by fk_name to ensure grouping works correctly
        sorted_fks = sorted(foreign_keys, key=attrgetter('fk_name'))

        # Group by fk_name and create combined mappings
        for fk_name, group in groupby(sorted_fks, key=attrgetter('fk_name')):
            group_list = list(group)
            # All FKs in a group should point to the same target collection
            result[fk_name] = {
                "foreign_collection": group_list[0].target_collection,
                "column_mapping": {
                    fk.field_name: fk.target_field
                    for fk in group_list
                }
            }

        return result

    def to_json(self) -> Dict[str, Any]:
        """
        Convert a single foreign key to a JSON-compatible dictionary.
        This is useful when dealing with individual foreign keys.
        """
        return {
            "foreign_collection": self.target_collection,
            "column_mapping": {
                self.field_name: self.target_field
            }
        }
