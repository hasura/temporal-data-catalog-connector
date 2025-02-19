from typing import Optional, Dict, Any, Type, List

from sqlalchemy import String, Text, DateTime, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, Session, relationship

from .compliance_tag import ComplianceTag
from .data_contract_status import DataContractStatus
from .documentation_reference import DocumentationReference
from .person import Person
from .usage_restriction import UsageRestriction
from ..base import Base
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..object_type.object_type_base import ObjectType


class DataContract(Base):
    """
    A class representing a data contract with additional hasura_metadata_manager
    for a data product specification.
    """
    __tablename__ = "data_contract"

    # Primary keys to create a 1:1 mapping with ObjectType
    subgraph_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    object_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Relationship to ObjectType (1:1 mapping)
    object_type: Mapped["ObjectType"] = TemporalRelationship(
        "ObjectType",
        uselist=False,
        primaryjoin="""and_(
            foreign(DataContract.object_type_name) == ObjectType.name,
            foreign(DataContract.subgraph_name) == ObjectType.subgraph_name
        )"""
    )

    # Relationships to supporting classes
    usage_restrictions: Mapped[List["UsageRestriction"]] = relationship(
        "UsageRestriction",
        primaryjoin="""and_(
            foreign(UsageRestriction.data_contract_subgraph_name) == DataContract.subgraph_name,
            foreign(UsageRestriction.data_contract_object_type_name) == DataContract.object_type_name
        )""",
        cascade="all, delete-orphan"
    )

    compliance_tags: Mapped[List["ComplianceTag"]] = relationship(
        "ComplianceTag",
        primaryjoin="""and_(
            foreign(ComplianceTag.data_contract_subgraph_name) == DataContract.subgraph_name,
            foreign(ComplianceTag.data_contract_object_type_name) == DataContract.object_type_name
        )""",
        cascade="all, delete-orphan"
    )

    # SLA and Performance Metadata
    sla_response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    sla_availability_percentage: Mapped[Optional[float]]
    max_records_per_request: Mapped[Optional[int]] = mapped_column(Integer)

    # Ownership and Governance
    owner_team: Mapped[Optional[str]] = mapped_column(String(255))
    owner_email: Mapped[Optional[str]] = mapped_column(String(255))
    owner: Mapped[Optional[Person]] = TemporalRelationship(
        Person,
        uselist=False,
        primaryjoin="and_(foreign(Person.email) == DataContract.owner_email)"
    )

    steward_email: Mapped[Optional[str]] = mapped_column(String(255))
    steward: Mapped[Optional[Person]] = TemporalRelationship(
        Person,
        uselist=False,
        primaryjoin="and_(foreign(Person.email) == DataContract.steward_email)"
    )

    # Contract Status and Versioning
    status: Mapped[DataContractStatus] = mapped_column(Enum(DataContractStatus), default=DataContractStatus.DRAFT)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")

    # Quality and Validation Constraints
    quality_rules: Mapped[Optional[str]] = mapped_column(Text,
                                                         comment="JSON Schema for defining data quality constraints and validation rules")

    # Temporal Metadata
    effective_date: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    expiration_date: Mapped[Optional[DateTime]] = mapped_column(DateTime)

    # Documentation References
    documentation_references: Mapped[List[DocumentationReference]] = relationship(
        DocumentationReference,
        primaryjoin="""and_(
            foreign(DocumentationReference.data_contract_subgraph_name) == DataContract.subgraph_name,
            foreign(DocumentationReference.data_contract_object_type_name) == DataContract.object_type_name
        )""",
        cascade="all, delete-orphan"
    )

    @classmethod
    def from_json(cls: Type["DataContract"], json_data: Dict[str, Any], object_type: "ObjectType",
                  session: Session) -> "DataContract":
        """
        Create a DataContract from JSON data associated with an ObjectType.

        :param json_data: Dictionary containing data contract hasura_metadata_manager
        :param object_type: The associated ObjectType
        :param session: SQLAlchemy session
        :return: Created DataContract instance
        """
        # Determine owner and steward
        owner = None
        if json_data.get('owner'):
            owner = Person.from_json(json_data['owner'], session)

        steward = None
        if json_data.get('steward'):
            steward = Person.from_json(json_data['steward'], session)

        # Create the DataContract
        data_contract = cls(
            subgraph_name=object_type.subgraph_name,
            object_type_name=object_type.name,

            # SLA and Performance Metadata
            sla_response_time_ms=json_data.get('slaResponseTimeMs'),
            sla_availability_percentage=json_data.get('slaAvailabilityPercentage'),
            max_records_per_request=json_data.get('maxRecordsPerRequest'),

            # Ownership and Governance
            owner_team=json_data.get('ownerTeam'),
            owner_email=owner.email if owner else None,
            steward_email=steward.email if steward else None,

            # Contract Status and Versioning
            status=json_data.get('status', DataContractStatus.DRAFT),
            version=json_data.get('version', '1.0.0'),

            # Quality and Validation Constraints
            quality_rules=json_data.get('qualityRules'),

            # Temporal Metadata
            effective_date=json_data.get('effectiveDate'),
            expiration_date=json_data.get('expirationDate')
        )

        session.add(data_contract)

        # Handle Usage Restrictions
        if json_data.get('usageRestrictions'):
            from .usage_restriction import UsageRestriction
            for restriction_data in json_data['usageRestrictions']:
                UsageRestriction.from_dict(
                    restriction_data,
                    data_contract.subgraph_name,
                    data_contract.object_type_name,
                    session
                )

        # Handle Compliance Tags
        if json_data.get('complianceTags'):
            from .compliance_tag import ComplianceTag
            for tag_data in json_data['complianceTags']:
                ComplianceTag.from_dict(
                    tag_data,
                    data_contract.subgraph_name,
                    data_contract.object_type_name,
                    session
                )

        # Handle Documentation References
        if json_data.get('documentationReferences'):
            for doc_ref_data in json_data['documentationReferences']:
                DocumentationReference.from_dict(
                    doc_ref_data,
                    data_contract.subgraph_name,
                    data_contract.object_type_name,
                    session
                )

        return data_contract

    def to_json(self) -> dict:
        """
        Convert DataContract to JSON representation.

        :return: Dictionary representation of the data contract
        """
        return {
            # SLA and Performance Metadata
            'slaResponseTimeMs': self.sla_response_time_ms,
            'slaAvailabilityPercentage': self.sla_availability_percentage,
            'maxRecordsPerRequest': self.max_records_per_request,

            # Ownership and Governance
            'ownerTeam': self.owner_team,
            'owner': self.owner.to_json() if self.owner else None,
            'steward': self.steward.to_json() if self.steward else None,

            # Contract Status and Versioning
            'status': self.status.value,
            'version': self.version,

            # Usage Restrictions
            'usageRestrictions': [
                {
                    'type': restriction.restriction_type,
                    'description': restriction.description,
                    'severity': restriction.severity
                } for restriction in self.usage_restrictions
            ],

            # Compliance Tags
            'complianceTags': [
                {
                    'name': tag.tag_name,
                    'description': tag.description,
                    'category': tag.tag_category
                } for tag in self.compliance_tags
            ],

            # Temporal Metadata
            'effectiveDate': self.effective_date,
            'expirationDate': self.expiration_date,

            # Quality and Validation Constraints
            'qualityRules': self.quality_rules,

            # Documentation References
            'documentationReferences': [
                doc_ref.to_dict() for doc_ref in self.documentation_references
            ],

            # Reference to the associated ObjectType
            'objectTypeName': self.object_type_name,
            'subgraphName': self.subgraph_name
        }
