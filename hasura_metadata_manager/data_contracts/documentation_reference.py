from typing import Optional, Dict, Any

from sqlalchemy import String, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, Session, relationship

from ..base import Base


class DocumentationReferenceType(str, Enum):
    """
    Enum to represent different types of documentation references.
    """
    DATA_CATALOG = "data_catalog"  # Link to a data catalog entry
    MARKDOWN = "markdown"  # Inline markdown documentation
    EXTERNAL_URL = "external_url"  # External documentation URL
    INTERNAL_WIKI = "internal_wiki"  # Internal wiki page reference
    RUNBOOK = "runbook"  # Operational runbook reference


class DocumentationReference(Base):
    """
    Represents a documentation reference for a data contract.
    Supports multiple sources of documentation.
    """
    __tablename__ = "documentation_reference"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign key to link with DataContract
    data_contract_subgraph_name: Mapped[str] = mapped_column(String(255), ForeignKey('data_contract.subgraph_name'))
    data_contract_object_type_name: Mapped[str] = mapped_column(String(255),
                                                                ForeignKey('data_contract.object_type_name'))

    # Documentation type and content
    reference_type: Mapped[DocumentationReferenceType] = mapped_column(Enum(DocumentationReferenceType))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    content: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)

    # Additional hasura_metadata_manager
    description: Mapped[Optional[str]] = mapped_column(Text)
    version: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationship back to DataContract
    data_contract: Mapped['DataContract'] = relationship('DataContract', back_populates='documentation_references')

    @classmethod
    def from_dict(cls, doc_ref_data: Dict[str, Any],
                  data_contract_subgraph_name: str,
                  data_contract_object_type_name: str,
                  session: Session) -> 'DocumentationReference':
        """
        Create a DocumentationReference from a dictionary of data.

        :param doc_ref_data: Dictionary containing documentation reference details
        :param data_contract_subgraph_name: Subgraph name of the associated data contract
        :param data_contract_object_type_name: Object type name of the associated data contract
        :param session: SQLAlchemy session
        :return: Created DocumentationReference instance
        """
        # Validate reference type
        reference_type = doc_ref_data.get('type', DocumentationReferenceType.EXTERNAL_URL)

        # Create documentation reference
        doc_ref = cls(
            data_contract_subgraph_name=data_contract_subgraph_name,
            data_contract_object_type_name=data_contract_object_type_name,
            reference_type=reference_type,
            title=doc_ref_data.get('title'),
            description=doc_ref_data.get('description'),
            version=doc_ref_data.get('version')
        )

        # Set content based on reference type
        if reference_type == DocumentationReferenceType.MARKDOWN:
            doc_ref.content = doc_ref_data.get('content')
        else:
            doc_ref.url = doc_ref_data.get('url')

        session.add(doc_ref)
        return doc_ref

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert DocumentationReference to a dictionary representation.

        :return: Dictionary representation of the documentation reference
        """
        base_dict = {
            'type': self.reference_type.value,
            'title': self.title,
            'description': self.description,
            'version': self.version
        }

        # Add content or URL based on reference type
        if self.reference_type == DocumentationReferenceType.MARKDOWN:
            base_dict['content'] = self.content
        else:
            base_dict['url'] = self.url

        return base_dict
