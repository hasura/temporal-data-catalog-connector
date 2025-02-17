# model_argument.py
from typing import TYPE_CHECKING, Type, Dict, Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .model import Model


class ModelArgument(Base):
    __tablename__ = "model_argument"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    model: Mapped["Model"] = TemporalRelationship(
        "Model",
        uselist=False,
        primaryjoin="""and_(
            foreign(ModelArgument.model_name) == Model.name, 
            foreign(ModelArgument.subgraph_name) == Model.subgraph_name
        )""", )

    @classmethod
    def from_json(cls: Type["ModelArgument"], json_data: Dict[str, Any],
                  model_name: str, subgraph_name: str) -> "ModelArgument":
        return cls(
            model_name=model_name,
            subgraph_name=subgraph_name,
            name=json_data["name"]
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "name": self.name
        }
