from datetime import datetime
from typing import Dict, Any, Optional, Type, TypeVar

from sqlalchemy import and_
from sqlalchemy.orm import Session

T = TypeVar('T', bound='TemporalSerializerMixin')


class TemporalSerializerMixin:
    """
    Mixin that adds temporal serialization capabilities.
    Works with models that have to_json() method for serialization.
    Automatically detects primary key fields.
    """

    @classmethod
    def _get_primary_key_filter(cls, data: Dict[str, Any]):
        """
        Automatically creates a filter based on primary key columns.
        """
        # Get primary key columns from SQLAlchemy hasura_metadata_manager
        primary_key_columns = [col for col in cls.__table__.columns if col.primary_key]

        if not primary_key_columns:
            raise ValueError(f"No primary key defined for {cls.__name__}")

        # Create filter conditions for each primary key column
        conditions = []
        missing_keys = []

        for col in primary_key_columns:
            # Use the column name as the key in the data dict
            if col.name not in data:
                missing_keys.append(col.name)
                continue

            conditions.append(col == data[col.name])

        if missing_keys:
            raise ValueError(
                f"Missing primary key fields for {cls.__name__}: {', '.join(missing_keys)}"
            )

        # Combine all conditions with AND
        return and_(*conditions)

    @classmethod
    def from_json_as_of(
            cls: Type[T],
            session: Session,
            data: Dict[str, Any],
            as_of_date: datetime
    ) -> Optional[T]:
        """
        Get an object as it existed at a specific point in time.

        Args:
            session: SQLAlchemy session
            data: Dictionary containing object data (must contain primary key fields)
            as_of_date: The point in time to retrieve
        """
        # Query the object as it existed at the specified time using primary key
        obj = (session.query(cls)
               .filter(cls._get_primary_key_filter(data))
               .filter(cls.created_at <= as_of_date)
               .filter(
            (cls.updated_at > as_of_date) |
            ((cls.is_current == True) & (cls.updated_at <= as_of_date))
        )
               .first())

        return obj
