from typing import Dict, Any, List, Type, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from .model_source_argument_mapping import ModelSourceArgumentMapping
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from ..model import Model


class ModelSourceConfig(Base):
    __tablename__ = "model_source_config"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    collection: Mapped[str] = mapped_column(String(255))
    data_connector_name: Mapped[str] = mapped_column(String(255))

    model: Mapped["Model"] = TemporalRelationship(
        "Model",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelSourceConfig.model_name) == Model.name, 
            foreign(ModelSourceConfig.subgraph_name) == Model.subgraph_name
        )"""
    )

    argument_mappings: Mapped[List["ModelSourceArgumentMapping"]] = TemporalRelationship(
        "ModelSourceArgumentMapping",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelSourceConfig.model_name) == ModelSourceArgumentMapping.model_name, 
            foreign(ModelSourceConfig.subgraph_name) == ModelSourceArgumentMapping.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["ModelSourceConfig"], json_data: Dict[str, Any],
                  model_name: str, subgraph_name: str, session: Session) -> "ModelSourceConfig":
        source_config = cls(
            model_name=model_name,
            subgraph_name=subgraph_name,
            collection=json_data["collection"],
            data_connector_name=json_data["dataConnectorName"]
        )
        session.add(source_config)
        session.flush()
        


        # Create argument mappings using their from_json method
        for key, value in json_data.get("argumentMapping", {}).items():
            mapping = ModelSourceArgumentMapping.from_json(
                key=key,
                value=value,
                model_name=model_name,
                subgraph_name=subgraph_name
            )
            mapping.source_config = source_config
            session.add(mapping)
            session.flush()
            


        return source_config

    def to_json(self) -> Dict[str, Any]:
        # Combine all argument mapping dictionaries
        argument_mapping = {}
        for mapping in self.argument_mappings:
            argument_mapping.update(mapping.to_json())

        return {
            "collection": self.collection,
            "dataConnectorName": self.data_connector_name,
            "argumentMapping": argument_mapping
        }
