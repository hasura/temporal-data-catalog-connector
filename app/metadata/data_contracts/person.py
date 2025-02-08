from typing import Optional, Any, Dict, List, Type, cast

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, Session

from ..base import Base


class Person(Base):
    """
    Represents a person with detailed contact and organizational information.
    """
    __tablename__ = "person"

    # Unique identifier for the person
    email: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Personal Information
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    preferred_name: Mapped[Optional[str]] = mapped_column(String(100))

    # Contact Information
    work_phone: Mapped[Optional[str]] = mapped_column(String(50))
    mobile_phone: Mapped[Optional[str]] = mapped_column(String(50))

    # Organizational Information
    department: Mapped[Optional[str]] = mapped_column(String(255))
    team: Mapped[Optional[str]] = mapped_column(String(255))
    job_title: Mapped[Optional[str]] = mapped_column(String(255))

    # Additional Contact Methods
    slack_handle: Mapped[Optional[str]] = mapped_column(String(100))
    github_username: Mapped[Optional[str]] = mapped_column(String(100))

    # Capability and Role Tracking
    areas_of_expertise: Mapped[Optional[List[str]]] = mapped_column(Text)

    # Relationships to other entities (to be defined in respective classes)
    # data_contract_ownerships: Relationship to DataContracts where this person is an owner
    # data_contract_stewardships: Relationship to DataContracts where this person is a steward

    @classmethod
    def from_json(cls: Type["Person"], json_data: Dict[str, Any], session: Session) -> "Person":
        """
        Create a Person from JSON data.

        :param json_data: Dictionary containing person details
        :param session: SQLAlchemy session
        :return: Created Person instance
        """
        # Validate email is present
        email = json_data.get('email')
        if not email:
            raise ValueError("Email is required to create a Person")

        # Check if person already exists
        existing_person = cast(Person, session.query(cls).filter_by(email=email).first())
        if existing_person:
            # Update existing person
            for key, value in json_data.items():
                if hasattr(existing_person, key):
                    setattr(existing_person, key, value)
            return existing_person

        # Create new person
        person = cls(
            email=email,
            first_name=json_data.get('firstName'),
            last_name=json_data.get('lastName'),
            preferred_name=json_data.get('preferredName'),
            work_phone=json_data.get('workPhone'),
            mobile_phone=json_data.get('mobilePhone'),
            department=json_data.get('department'),
            team=json_data.get('team'),
            job_title=json_data.get('jobTitle'),
            slack_handle=json_data.get('slackHandle'),
            github_username=json_data.get('githubUsername'),
            areas_of_expertise=json_data.get('areasOfExpertise')
        )

        session.add(person)
        return person

    def to_json(self) -> Dict[str, Any]:
        """
        Convert Person to JSON representation.

        :return: Dictionary representation of the person
        """
        return {
            'email': self.email,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'preferredName': self.preferred_name,
            'workPhone': self.work_phone,
            'mobilePhone': self.mobile_phone,
            'department': self.department,
            'team': self.team,
            'jobTitle': self.job_title,
            'slackHandle': self.slack_handle,
            'githubUsername': self.github_username,
            'areasOfExpertise': self.areas_of_expertise
        }

    @property
    def full_name(self) -> str:
        """
        Generate a full name for the person.

        :return: Formatted full name
        """
        if self.preferred_name:
            return self.preferred_name
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email
