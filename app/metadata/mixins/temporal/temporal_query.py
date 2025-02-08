from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query

from .temporal_exception import TemporalException


class TemporalQuery(Query):
    """Enhanced query class with temporal filtering capabilities"""

    def __init__(self, entities, *args, **kwargs):
        super().__init__(entities, *args, **kwargs)
        self._temporal_filter_applied = False
        self._as_of_date = None

    def __iter__(self):
        # Apply temporal filtering before iteration if not already applied
        if not self._temporal_filter_applied:
            return self.temporal_filter().__iter__()
        return super().__iter__()

    def _get_entity_from_query(self):
        """Helper method to safely get the primary entity from the query"""
        if hasattr(self, '_select_from_entity') and self._select_from_entity:
            return self._select_from_entity
        if hasattr(self, 'selectable') and hasattr(self.selectable, 'froms'):
            # Try to get entity from selectable.froms
            if self.selectable.froms:
                return self.selectable.froms[0]
        if self._raw_columns:
            return self._raw_columns[0]
        return None

    def temporal_filter(self):
        """Apply temporal filtering if not already applied"""
        if self._temporal_filter_applied:
            return self

        if self._as_of_date:
            return self.as_of(self._as_of_date)

        # Only apply to queries involving TemporalMixin classes
        primary_entity = self._get_entity_from_query()
        if primary_entity is None:
            return self

        mapper = getattr(primary_entity, 'mapper', getattr(primary_entity, '_bind_mapper', None))
        if mapper is None:
            return self

        needs_filtering = hasattr(mapper.class_, 'is_current')

        if needs_filtering:
            self = self.filter_by(is_current=True, is_deleted=False)
            self._temporal_filter_applied = True

        return self

    def get_primary_entity(self):
        """Get the primary entity being queried"""
        primary_entity = self._get_entity_from_query()
        if primary_entity is None:
            raise TemporalException("No entity found for temporal query")

        mapper = getattr(primary_entity, 'mapper', getattr(primary_entity, '_bind_mapper', None))
        if mapper is None:
            raise TemporalException("Could not determine mapper for entity")

        return mapper.class_

    def as_of(self, timestamp: datetime):
        """Query the state of records as they existed at the given timestamp"""
        self._as_of_date = timestamp
        self._temporal_filter_applied = True

        primary_entity = self._get_entity_from_query()
        if primary_entity is None:
            return self

        mapper = getattr(primary_entity, 'mapper', getattr(primary_entity, '_bind_mapper', None))
        if mapper is None:
            return self

        entity_class = mapper.class_
        if not hasattr(entity_class, 'created_at'):
            return self

        temporal_entities = [entity_class]

        if temporal_entities:
            conditions = []
            for entity in temporal_entities:
                conditions.append(
                    and_(
                        entity.created_at <= timestamp,
                        or_(
                            entity.updated_at is None,
                            entity.updated_at > timestamp
                        )
                    )
                )
            return self.filter(and_(*conditions))
        return self

    def between(self, start_date: datetime, end_date: datetime):
        """Get records that were active between the given dates"""
        self._temporal_filter_applied = True
        entity = self.get_primary_entity()

        return self.filter(
            and_(
                entity.created_at <= end_date,
                or_(
                    entity.updated_at is None,
                    entity.updated_at >= start_date
                )
            )
        )

    def versions_between(self, start_date: datetime, end_date: datetime):
        """Get all versions of records that changed between the given dates"""
        self._temporal_filter_applied = True
        entity = self.get_primary_entity()

        return self.filter(
            and_(
                entity.created_at.between(start_date, end_date),
                or_(
                    entity.updated_at is None,
                    entity.updated_at.between(start_date, end_date)
                )
            )
        )

    def changes_since(self, since_date: datetime):
        """Get records that have changed since the given date"""
        self._temporal_filter_applied = True
        entity = self.get_primary_entity()

        return self.filter(
            or_(
                entity.created_at >= since_date,
                and_(
                    entity.updated_at is not None,
                    entity.updated_at >= since_date
                )
            )
        )

    def include_deleted(self):
        """Allow querying of deleted records"""
        self._temporal_filter_applied = True
        return self.filter_by(is_current=True)

    def include_historical(self):
        """Allow querying of historical records"""
        self._temporal_filter_applied = True
        return self.filter_by(is_deleted=False)

    def unfiltered(self):
        """Disable temporal filtering entirely"""
        self._temporal_filter_applied = True
        return self
