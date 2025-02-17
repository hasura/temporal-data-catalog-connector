from typing import Dict, Any, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .relationship_rdf_mixin import RelationshipRDFMixin
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .. import Subgraph
    from ..relationship import Relationship


class RelationshipFieldMapping(Base, RelationshipRDFMixin):
    __tablename__ = "relationship_field_mapping"

    subgraph_name: Mapped[str] = mapped_column(String, primary_key=True)
    source_type_name: Mapped[str] = mapped_column(String, primary_key=True)
    relationship_name: Mapped[str] = mapped_column(String, primary_key=True)
    source_field: Mapped[str] = mapped_column(String, primary_key=True)
    target_field: Mapped[str] = mapped_column(String)

    @property
    def name(self):
        return f"{self.source_field} == {self.target_field}"

    parent_relationship: Mapped["Relationship"] = TemporalRelationship(
        "Relationship",
        uselist=False,
        primaryjoin="""and_(
            foreign(RelationshipFieldMapping.subgraph_name) == Relationship.subgraph_name, 
            foreign(RelationshipFieldMapping.source_type_name) == Relationship.source_type_name, 
            foreign(RelationshipFieldMapping.relationship_name) == Relationship.name 
        )"""
    )

    @classmethod
    def from_mapping_data(cls, mapping_data: Dict[str, Any],
                          relationship_name: str, subgraph: "Subgraph",
                          source_type_name: str, session: "Session") -> "RelationshipFieldMapping":
        """
        Create field mapping from a single mapping entry
        """
        source_fields = [field["fieldName"] for field in mapping_data["source"]["fieldPath"]]
        source_field = ','.join(source_fields)

        target_fields = [field["fieldName"] for field in mapping_data["target"]["modelField"]]
        target_field = ','.join(target_fields)

        result = cls(
            relationship_name=relationship_name,
            subgraph_name=subgraph.name,
            source_type_name=source_type_name,
            source_field=source_field,
            target_field=target_field
        )

        session.add(result)
        session.flush()
        return result
