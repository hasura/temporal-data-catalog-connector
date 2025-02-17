from typing import Optional, Dict, Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from .data_contract import DataContract
from ..base import Base


class UsageRestriction(Base):
    """
    Represents a specific usage restriction for a data contract.
    """
    __tablename__ = "usage_restriction"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data_contract_subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    data_contract_object_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    restriction_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationship to DataContract
    data_contract: Mapped[DataContract] = relationship(
        DataContract,
        primaryjoin="""and_(
            foreign(UsageRestriction.data_contract_subgraph_name) == DataContract.subgraph_name,
            foreign(UsageRestriction.data_contract_object_type_name) == DataContract.object_type_name
        )"""
    )

    @classmethod
    def from_dict(cls, restriction_data: Dict[str, Any],
                  data_contract_subgraph_name: str,
                  data_contract_object_type_name: str,
                  session: Session) -> 'UsageRestriction':
        """
        Create a UsageRestriction from a dictionary of data.

        :param restriction_data: Dictionary containing restriction details
        :param data_contract_subgraph_name: Subgraph name of the associated data contract
        :param data_contract_object_type_name: Object type name of the associated data contract
        :param session: SQLAlchemy session
        :return: Created UsageRestriction instance
        """
        restriction = cls(
            data_contract_subgraph_name=data_contract_subgraph_name,
            data_contract_object_type_name=data_contract_object_type_name,
            restriction_type=restriction_data.get('type', ''),
            description=restriction_data.get('description'),
            severity=restriction_data.get('severity')
        )
        session.add(restriction)
        return restriction

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert UsageRestriction to a dictionary representation.

        :return: Dictionary representation of the usage restriction
        """
        return {
            'type': self.restriction_type,
            'description': self.description,
            'severity': self.severity
        }
