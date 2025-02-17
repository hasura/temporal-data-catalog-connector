from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base
from .relationship_base import RelationshipType
from typing import Optional, Dict, Any


class TargetModel(Base):
    __tablename__ = "target_model"

    # Composite Primary Key matching relationship
    name: Mapped[str] = mapped_column(String, nullable=False)
    subgraph_name: Mapped[str] = mapped_column(String, primary_key=True)
    source_type_name: Mapped[str] = mapped_column(String, primary_key=True)
    relationship_name: Mapped[str] = mapped_column(String, primary_key=True)

    # Target specific fields
    relationship_type: Mapped[str] = mapped_column(String, nullable=False)
    target_subgraph: Mapped[Optional[str]] = mapped_column(String)
    is_command: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> Dict[str, Any]:
        base = {
            "name": self.name,
            "relationshipType": self.relationship_type,
            "subgraph": self.target_subgraph or self.subgraph_name
        }

        return {
            "command" if self.is_command else "model": base,
            "command" if not self.is_command else "model": None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], relationship_name: str,
                  subgraph_name: str, source_type_name: str) -> "TargetModel":

        if not all([relationship_name, subgraph_name, source_type_name]):
            raise ValueError("relationship_name, subgraph_name, and source_type_name cannot be null")

        if "model" in data and data["model"]:
            target_data = data["model"]
            is_command = False
        elif "command" in data and data["command"]:
            target_data = data["command"]
            is_command = True
        else:
            raise ValueError("Target must specify either model or command")

        return cls(
            name=target_data["name"],
            relationship_name=relationship_name,
            subgraph_name=subgraph_name,
            source_type_name=source_type_name,
            relationship_type=target_data.get("relationshipType", RelationshipType.OBJECT.value),
            target_subgraph=target_data.get("subgraph"),
            is_command=is_command
        )
