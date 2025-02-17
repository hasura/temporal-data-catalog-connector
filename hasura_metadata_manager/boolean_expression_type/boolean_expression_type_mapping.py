from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship


class BooleanExpressionTypeMapping(Base):
    """Association model between BooleanExpressionType and TypeDefinition"""
    __tablename__ = 'boolean_expression_type_mapping'

    # Primary key columns
    bool_expr_subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    bool_expr_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    type_def_connector_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    type_def_subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    type_def_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    @property
    def name(self) -> str:
        return self.bool_expr_name

    # Relationships
    boolean_expression_type = TemporalRelationship(
        "BooleanExpressionType",
        uselist=False,
        primaryjoin="""and_(
            foreign(BooleanExpressionTypeMapping.bool_expr_subgraph_name)==BooleanExpressionType.subgraph_name, 
            foreign(BooleanExpressionTypeMapping.bool_expr_name)==BooleanExpressionType.name
        )"""
    )

    def __repr__(self) -> str:
        return (f"<BooleanExpressionTypeMapping("
                f"bool_expr={self.bool_expr_name}, "
                f"type_def={self.type_def_name})>")
