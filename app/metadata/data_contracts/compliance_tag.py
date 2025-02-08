from typing import Optional, Dict, Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from .data_contract import DataContract
from ..base import Base


class ComplianceTag(Base):
    """
    Represents a compliance tag associated with a data contract.
    """
    __tablename__ = "compliance_tag"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data_contract_subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    data_contract_object_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    tag_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    tag_category: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationship to DataContract
    data_contract: Mapped[DataContract] = relationship(
        DataContract,
        primaryjoin="""and_(
            foreign(ComplianceTag.data_contract_subgraph_name) == DataContract.subgraph_name,
            foreign(ComplianceTag.data_contract_object_type_name) == DataContract.object_type_name
        )"""
    )

    @classmethod
    def from_dict(cls, tag_data: Dict[str, Any],
                  data_contract_subgraph_name: str,
                  data_contract_object_type_name: str,
                  session: Session) -> 'ComplianceTag':
        """
        Create a ComplianceTag from a dictionary of data.

        :param tag_data: Dictionary containing tag details
        :param data_contract_subgraph_name: Subgraph name of the associated data contract
        :param data_contract_object_type_name: Object type name of the associated data contract
        :param session: SQLAlchemy session
        :return: Created ComplianceTag instance
        """
        tag = cls(
            data_contract_subgraph_name=data_contract_subgraph_name,
            data_contract_object_type_name=data_contract_object_type_name,
            tag_name=tag_data.get('name', ''),
            description=tag_data.get('description'),
            tag_category=tag_data.get('category')
        )
        session.add(tag)
        return tag

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ComplianceTag to a dictionary representation.

        :return: Dictionary representation of the compliance tag
        """
        return {
            'name': self.tag_name,
            'description': self.description,
            'category': self.tag_category
        }
