from sqlalchemy import Column, Integer, ForeignKey, Enum, String
from sqlalchemy.orm import relationship

from .change_operation import ChangeOperation
from ...base.core_base import CoreBase


class DiffChange(CoreBase):
    """Table for storing individual field changes"""
    __tablename__ = 'diff_changes'

    id = Column(Integer, primary_key=True)
    diff_entry_id = Column(Integer, ForeignKey('diffs.id'), nullable=False)
    operation = Column(Enum(ChangeOperation), nullable=False)
    field_path = Column(String(255), nullable=False)  # The path to the changed field
    old_value = Column(String, nullable=True)  # Previous value (as string)
    new_value = Column(String, nullable=True)  # New value (as string)
    value_type = Column(String(50), nullable=False)  # Type of the value (e.g., 'str', 'int', 'bool')

    # Relationship back to diff entry
    diff_entry = relationship("DiffEntry", back_populates="changes")
