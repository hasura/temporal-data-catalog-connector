from typing import Dict, Any

from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column, Session

from .boolean_expression_type_base import BooleanExpressionType
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship

logger = __import__("logging").getLogger(__name__)


class DataConnectorOperatorMapping(Base):
    __tablename__ = "data_connector_operator_mapping"

    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    data_connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    boolean_expression_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    data_connector_scalar_type: Mapped[str] = mapped_column(String(255))
    operator_mapping: Mapped[Dict] = mapped_column(JSON, default=dict)

    boolean_expression_type: Mapped["BooleanExpressionType"] = TemporalRelationship(
        "BooleanExpressionType",
        uselist=False,
        primaryjoin="""and_(
            foreign(DataConnectorOperatorMapping.boolean_expression_type_name) == BooleanExpressionType.name,
            foreign(DataConnectorOperatorMapping.subgraph_name) == BooleanExpressionType.subgraph_name
        )"""
    )

    @classmethod
    def from_json(cls, json_data: Dict[str, Any], parent: "BooleanExpressionType",
                  session: Session) -> "DataConnectorOperatorMapping":
        logger.debug(f"Creating DataConnectorOperatorMapping for parent {parent.name}")

        mapping = cls(
            subgraph_name=parent.subgraph_name,
            boolean_expression_type_name=parent.name,
            data_connector_name=json_data.get("dataConnectorName"),
            data_connector_scalar_type=json_data.get("dataConnectorScalarType"),
            operator_mapping=json_data.get("operatorMapping", {})
        )
        logger.debug(f"Created DataConnectorOperatorMapping for connector {mapping.data_connector_name} "
                     f"with scalar_type={mapping.data_connector_scalar_type}")

        session.add(mapping)
        session.flush()
        return mapping

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary"""
        return {
            "dataConnectorName": self.data_connector_name,
            "dataConnectorScalarType": self.data_connector_scalar_type,
            "operatorMapping": self.operator_mapping
        }
