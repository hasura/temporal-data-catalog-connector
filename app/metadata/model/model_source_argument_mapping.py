from typing import Type, Dict, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .model_source_config import ModelSourceConfig


class ModelSourceArgumentMapping(Base):
    __tablename__ = "model_source_argument_mapping"

    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))

    source_config: Mapped["ModelSourceConfig"] = TemporalRelationship(
        "ModelSourceConfig",
        uselist=False,
        primaryjoin="""and_(
            foreign(ModelSourceArgumentMapping.model_name) == ModelSourceConfig.model_name, 
            foreign(ModelSourceArgumentMapping.subgraph_name) == ModelSourceConfig.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls: Type["ModelSourceArgumentMapping"], key: str, value: str,
                  model_name: str, subgraph_name: str) -> "ModelSourceArgumentMapping":
        return cls(
            model_name=model_name,
            subgraph_name=subgraph_name,
            key=key,
            value=value
        )

    def to_json(self) -> Dict[str, str]:
        return {
            self.key: self.value
        }
