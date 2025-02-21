from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from ...base.core_base import CoreBase


class   DiffEntry(CoreBase):
    """Table for storing hasura_metadata_manager about version changes"""
    __tablename__ = 'diffs'

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(100), nullable=False)  # The type of entity (e.g., 'mutation_capability')
    t_id = Column(String(2056), nullable=False)  # Reference to the t_id of the source entity
    from_version = Column(Integer, nullable=False)  # Previous version number
    to_version = Column(Integer, nullable=False)  # New version number
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))

    # Relationship to individual changes
    changes = relationship("DiffChange", back_populates="diff_entry", cascade="all, delete-orphan")
