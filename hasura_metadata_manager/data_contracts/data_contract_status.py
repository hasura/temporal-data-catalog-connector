from sqlalchemy import Enum


class DataContractStatus(str, Enum):
    """Enum to represent the status of a data contract."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
