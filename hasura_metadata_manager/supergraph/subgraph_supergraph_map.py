from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .supergraph_base import Supergraph
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..subgraph.subgraph_base import Subgraph


class SubgraphSupergraphMap(Base):
    __tablename__ = "subgraph_supergraph_map"

    supergraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        primaryjoin="and_(foreign(SubgraphSupergraphMap.subgraph_name) == Subgraph.name)",
        uselist=True
    )
    supergraph: Mapped["Supergraph"] = TemporalRelationship(
        "Supergraph",
        primaryjoin="and_(foreign(SubgraphSupergraphMap.supergraph_name) == Supergraph.name)",
        uselist=True
    )
