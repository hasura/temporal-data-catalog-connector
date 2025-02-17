from sqlalchemy import Enum


class PersonRole(str, Enum):
    """
    Enum to represent different roles a person can have
    in relation to a data product or contract.
    """
    OWNER = "owner"
    STEWARD = "steward"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    CURATOR = "curator"
    TECHNICAL_LEAD = "technical_lead"
    BUSINESS_LEAD = "business_lead"
