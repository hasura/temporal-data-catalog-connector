import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, cast
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Boolean, event, inspect, and_, or_, Index, \
    PrimaryKeyConstraint
from sqlalchemy.orm import Session, MappedColumn
from sqlalchemy.orm import declared_attr
from sqlalchemy.orm import foreign
from sqlalchemy.orm import registry

from .change_operation import ChangeOperation
from .diff_change import DiffChange
from .diff_entry import DiffEntry
from .temporal_exception import TemporalException
from .temporal_query import TemporalQuery
from .temporal_relationship import TemporalRelationship

logger = logging.getLogger(__name__)


def get_or_create_registry():
    """
    Ensure a registry exists and return it.
    Automatically patches the configure method to set up temporal indexes.

    This is not a true singleton, but provides a way to ensure
    a registry is available.
    """
    global _global_registry
    if '_global_registry' not in globals():
        _global_registry = registry()

        # Patch the configure method for this registry
        original_configure = _global_registry.configure

        def patched_configure(*args, **kwargs):
            """
            Wrap the original configure method to add temporal index setup.
            """
            original_configure(*args, **kwargs)

            # Setup temporal indexes for all mappers in this registry
            for mapper in _global_registry.mappers:
                cls = mapper.class_
                if issubclass(cls, TemporalMixin):
                    cls._create_temporal_indexes(mapper)

        # Replace the configure method for this specific registry
        _global_registry.configure = patched_configure

    return _global_registry


# Create a global default registry
_global_registry = get_or_create_registry()


class TemporalMixin:
    """
    A mixin that adds temporal tracking to SQLAlchemy models.
    Tracks creation, updates, versions, maintains history, and handles soft deletes.
    """
    query_class = TemporalQuery

    # Version must be part of PK to allow multiple versions of same business entity
    t_version = Column(Integer, nullable=False, default=1)

    @classmethod
    def get_business_key_params(cls, obj) -> Dict[str, Any]:
        """
        Extract business key values from an object.

        :param obj: The object to extract business key values from
        :return: Dictionary of business key names to their values
        """
        params = {}
        for pk in cls.get_business_keys():
            value = getattr(obj, pk, None)
            if value is None:
                return None  # Return None if any business key is missing
            params[pk] = value
        return params

    @classmethod
    def generate_t_id(cls, params: Dict[str, Any] = None) -> str:
        """
        Generate t_id from business keys.

        :param params: Optional dictionary of parameters. If None, uses current instance attributes.
        :return: Generated t_id string
        """
        # If no params provided, use current instance's attributes
        if params is None:
            params = {}

        pk_values = []
        for pk in cls.get_business_keys():
            # Try to get value from provided params
            value = params.get(pk)
            if value is None:
                continue
            pk_values.append(f"{pk}:{value}")

        return f"{cls.__name__.lower()}:{'-'.join(pk_values)}" if pk_values else None

    @declared_attr
    def t_id(cls):
        """Generate t_id from business keys only (not version)"""

        def generate_t_id(context):
            params = context.get_current_parameters()
            return cls._generate_t_id(params)

        return Column(
            't_id',
            String(2056),
            nullable=False,
            default=generate_t_id
        )

    # Add a flag to control timestamp generation
    _override_created_at = False
    _override_timestamp = None

    @classmethod
    def _generate_t_id(cls, params: Dict[str, Any] = None) -> str:
        """
        Generate t_id from business keys.

        :param params: Optional dictionary of parameters. If None, uses current instance attributes.
        :return: Generated t_id string
        """
        # If no params provided, use current instance's attributes
        if params is None:
            params = {}

        pk_values = []
        for pk in cls.get_business_keys():
            # Try to get value from provided params, fall back to current instance if needed
            value = params.get(pk)
            if value is None:
                continue
            pk_values.append(f"{pk}:{value}")

        return f"{cls.__name__.lower()}:{'-'.join(pk_values)}" if pk_values else None

    @classmethod
    def set_override_timestamp(cls, timestamp):
        """
        Set a global override timestamp for all new records
        """
        cls._override_created_at = True
        cls._override_timestamp = timestamp

    @classmethod
    def clear_override_timestamp(cls):
        """
        Clear the override timestamp
        """
        cls._override_created_at = False
        cls._override_timestamp = None

    @declared_attr
    def t_created_at(cls):
        def generate_created_at():
            if cls._override_created_at and cls._override_timestamp:
                return cls._override_timestamp
            return datetime.now(timezone.utc)

        return Column(
            't_created_at',
            DateTime,
            nullable=False,
            default=generate_created_at
        )

    # Temporal tracking columns
    t_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    t_is_current = Column(Boolean, nullable=False, default=True)
    t_content_hash = Column(String(64), nullable=False)  # SHA-256 hash
    t_is_deleted = Column(Boolean, nullable=False, default=False)  # Soft delete flag
    t_deleted_at = Column(DateTime, nullable=True)  # When the record was soft deleted

    # Class variable to store initialization timestamp
    _initialization_timestamp = None

    @classmethod
    def set_initialization_timestamp(cls, timestamp: datetime):
        """
        Set the global initialization timestamp
        """
        cls._initialization_timestamp = timestamp

    @classmethod
    def get_initialization_timestamp(cls) -> Optional[datetime]:
        """
        Retrieve the global initialization timestamp
        """
        return cls._initialization_timestamp

    @declared_attr
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}"

    @declared_attr
    def __table_args__(cls):
        """
        Dynamically set table arguments to include t_version in primary key.
        """
        # Try to get primary key columns from mapper args or class attributes
        pk_columns = []
        for name, column in cls.__dict__.items():
            # Initialize a variable to hold the unwrapped column (if needed)
            unwrapped_column = column

            # Check if it's a Mapped or MappedColumn and unwrap to get the actual column
            if isinstance(column, MappedColumn):
                unwrapped_column = column.column
                # logger.debug(f"Unwrapped Mapped/MappedColumn: {name} -> {unwrapped_column}")

            # Check if the unwrapped column is a SQLAlchemy Column
            if hasattr(unwrapped_column, 'primary_key'):
                logger.debug(f"SQLAlchemy Column found: {name}")
                logger.debug(f"  {name}.primary_key: {getattr(unwrapped_column, 'primary_key', None)}")
                logger.debug(f"  {name}.__class__: {unwrapped_column.__class__.__name__}")
                logger.debug(f"  {name}.type: {getattr(unwrapped_column, 'type', None)}")
            else:
                # If this is some other type of attribute, log its class
                logger.debug(f"Non-column attribute: {name} ({column.__class__.__name__})")

            # Check if the unwrapped column is marked as a primary key
            if hasattr(unwrapped_column, 'primary_key') and unwrapped_column.primary_key and name != 't_version':
                logger.debug(f"Adding '{name}' to pk_columns.")
                pk_columns.append(name)

        # Debug output of collected primary key columns
        logger.debug(f"Collected PK columns: {pk_columns}")

        # Debug output of collected pk_columns list
        logger.debug(f"Collected PK columns: {pk_columns}")

        # If we found primary key columns, create a new primary key constraint
        if pk_columns:
            pk_columns.append('t_version')
            return (
                PrimaryKeyConstraint(*pk_columns),
                {'extend_existing': True}
            )

        # Fallback
        return {'extend_existing': True}

    @declared_attr
    def diffs(cls):
        """Relationship to access diffs for this entity"""
        return TemporalRelationship(
            DiffEntry,
            primaryjoin=lambda: and_(
                foreign(DiffEntry.entity_type) == cls.__name__.lower(),
                foreign(DiffEntry.t_id) == cls.t_id
            ),
            overlaps='diffs',
            order_by=DiffEntry.to_version,
            sync_backref=False
        )

    @classmethod
    def _create_temporal_indexes(cls, mapper):
        """Automatically create temporal indexes for the class."""
        if not mapper:
            return

        # Get business key columns (primary keys excluding version)
        business_keys = [col for col in mapper.primary_key if col.name != 't_version']
        if not business_keys:
            logger.warning(f"No business keys found for temporal class {cls.__name__}")
            return

        # Use the table from the mapper instead of __table__
        table = mapper.mapped_table

        # Create business keys index if it doesn't exist
        bk_idx_name = f'ix_{cls.__tablename__}_business_keys'
        if bk_idx_name not in [i.name for i in table.indexes]:
            Index(bk_idx_name, *business_keys)

        # Create temporal current index if it doesn't exist
        tc_idx_name = f'ix_{cls.__tablename__}_temporal_current'
        if tc_idx_name not in [i.name for i in table.indexes]:
            Index(tc_idx_name, 't_id', 't_is_current', 't_is_deleted')

    @classmethod
    def as_of(cls, session: Session, timestamp: datetime):
        """
        Convenience method to query entities as of a specific time.
        Returns a query object filtered to show state as of the given timestamp.
        """
        query = session.query(cls).with_session(session)
        query._as_of_date = timestamp
        query._temporal_filter_applied = True

        return query.filter(
            and_(
                cls.t_created_at <= timestamp,
                or_(
                    cls.t_updated_at is None,
                    cls.t_updated_at > timestamp
                )
            )
        )

    @classmethod
    def current_state(cls, session: Session):
        """Convenience method to query current state entities"""
        return session.query(cls).filter_by(t_is_current=True, t_is_deleted=False)

    @classmethod
    def get_primary_keys(cls) -> List[str]:
        """Get all primary key column names including t_version"""
        mapper = inspect(cls)
        if not mapper.primary_key:
            raise TemporalException(f"Model {cls.__name__} has no primary key defined")
        return [key.name for key in mapper.primary_key]

    @classmethod
    def get_business_keys(cls) -> List[str]:
        """Get business key columns (primary keys excluding t_version)"""
        return [key for key in cls.get_primary_keys() if key != 't_version']

    def _get_non_temporal_attrs(self) -> dict:
        """
        Helper method to get all non-temporal column attributes of the entity.
        Excludes:
        - SQLAlchemy internal fields (starting with '_')
        - Temporal fields (starting with 't_')
        - Known temporal-like fields
        - Relationships
        - Properties
        - Non-column attributes

        Returns:
            dict: Dictionary of column name to value pairs
        """
        # Expanded list of temporal-like field names to exclude
        TEMPORAL_FIELD_PREFIXES = ['t_', 'last_updated', 'created_', 'updated_']

        # Get the mapper for this class
        mapper = inspect(self).mapper

        # Get all regular column attributes (excluding relationships and properties)
        column_attrs = {
            key: getattr(self, key)
            for key in sorted(mapper.columns.keys())  # Use columns from mapper
            if not any(key.startswith(prefix) for prefix in TEMPORAL_FIELD_PREFIXES)
        }

        return column_attrs

    def calculate_content_hash(self) -> str:
        """Calculate a hash of the entity's content, excluding temporal tracking fields."""
        content = self._get_non_temporal_attrs()
        return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()

    def calculate_changes(self, previous: Optional['TemporalMixin']) -> List[Dict[str, Any]]:

        # If this is just a soft delete operation and no other changes, skip additional diff creation
        if (self.t_is_deleted != previous.t_is_deleted and
                self._get_non_temporal_attrs() == previous._get_non_temporal_attrs()):
            return []

        """Calculate the changes between this version and the previous version"""
        # If no previous version exists, check for new record tracking
        if not previous:
            # Track as an add if it's the first version and created after initialization
            if (self.t_version == 1 and
                    self.t_created_at and
                    self.get_initialization_timestamp() and
                    self.t_created_at > self.get_initialization_timestamp()):
                return [{
                    'operation': ChangeOperation.ADD,
                    'field_path': '/',
                    'old_value': None,
                    'new_value': self._serialize_value(self._get_non_temporal_attrs()),
                    'value_type': 'dict'
                }]
            return []

        current_state = self._get_non_temporal_attrs()
        previous_state = previous._get_non_temporal_attrs()

        changes = []

        # If this is a soft delete or restore operation
        if self.t_is_deleted != previous.t_is_deleted:
            operation = ChangeOperation.DELETE if self.t_is_deleted else ChangeOperation.RESTORE
            changes.append({
                'operation': operation,
                'field_path': '/',
                'old_value': None,
                'new_value': None,
                'value_type': 'null'
            })

        # Handle modified and removed fields
        for key, prev_value in previous_state.items():
            if key not in current_state:
                changes.append({
                    'operation': ChangeOperation.REMOVE,
                    'field_path': f'/{key}',
                    'old_value': self._serialize_value(prev_value),
                    'new_value': None,
                    'value_type': self._get_value_type(prev_value)
                })
            elif current_state[key] != prev_value:
                changes.append({
                    'operation': ChangeOperation.REPLACE,
                    'field_path': f'/{key}',
                    'old_value': self._serialize_value(prev_value),
                    'new_value': self._serialize_value(current_state[key]),
                    'value_type': self._get_value_type(current_state[key])
                })

        # Handle added fields
        for key, curr_value in current_state.items():
            if key not in previous_state:
                changes.append({
                    'operation': ChangeOperation.ADD,
                    'field_path': f'/{key}',
                    'old_value': None,
                    'new_value': self._serialize_value(curr_value),
                    'value_type': self._get_value_type(curr_value)
                })

        return changes

    def get_version_at(self, version: int) -> Optional['TemporalMixin']:
        """Get the state of the entity at a specific version"""
        if version < 1:
            raise TemporalException("Version must be greater than 0")

        # Get all changes up to the requested version
        changes = []
        for diff_entry in self.diffs:
            if diff_entry.to_version <= version:
                for change in diff_entry.changes:
                    changes.append({
                        'operation': change.operation,
                        'field_path': change.field_path,
                        'old_value': change.old_value,
                        'new_value': change.new_value,
                        'value_type': change.value_type
                    })

        # Create a new instance with current values
        reconstructed = type(self)()
        base_state = self._get_non_temporal_attrs()

        # Apply changes in reverse to get to the requested version
        for change in reversed(changes):
            path = change['field_path'].strip('/')
            if path == '':  # This is a delete/restore operation
                continue

            if change['operation'] == ChangeOperation.ADD:
                base_state.pop(path, None)
            elif change['operation'] == ChangeOperation.REMOVE:
                base_state[path] = self._deserialize_value(change['old_value'], change['value_type'])
            elif change['operation'] == ChangeOperation.REPLACE:
                base_state[path] = self._deserialize_value(change['old_value'], change['value_type'])

        # Update the reconstructed instance
        for k, v in base_state.items():
            setattr(reconstructed, k, v)

        reconstructed.t_version = version
        return reconstructed

    def build_business_key_filter(self) -> Dict[str, Any]:
        """Build a filter dict for querying by business keys"""
        filter_dict = {}
        for key in self.get_business_keys():
            value = getattr(self, key, None)
            if value is None:
                raise TemporalException(f"Business key {key} cannot be None")
            filter_dict[key] = value
        return filter_dict

    @staticmethod
    def _get_value_type(value: Any) -> str:
        """Helper to get the type name of a value"""
        if value is None:
            return 'null'
        return type(value).__name__

    @staticmethod
    def _serialize_value(value: Any) -> Optional[str]:
        """Helper to serialize any value to string"""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _deserialize_value(value: str, value_type: str) -> Any:
        """Helper to deserialize a value from string based on its type"""
        if value is None:
            return None

        type_mapping = {
            'int': int,
            'float': float,
            'bool': lambda x: x.lower() == 'true',
            'dict': json.loads,
            'list': json.loads,
            'null': lambda x: None,
            'str': str,
            'datetime': lambda x: datetime.fromisoformat(x)
        }

        converter = type_mapping.get(value_type, str)
        try:
            return converter(value)
        except (ValueError, json.JSONDecodeError):
            return value

    def soft_delete(self, session: Session) -> None:
        """Soft delete the current record and create a new soft-deleted version"""
        # Store the current state before deletion
        previous_state = self._get_non_temporal_attrs()

        logger.info(f"Soft-deleting temporal {self.t_id}")

        # Create a new soft-deleted version
        soft_deleted_obj = type(self)()

        # Copy all attributes except temporal tracking
        for key, value in self.__dict__.items():
            if key != '_sa_instance_state':
                setattr(soft_deleted_obj, key, value)

        # Set soft delete specific attributes
        soft_deleted_obj.t_id = self.t_id
        soft_deleted_obj.t_is_deleted = True
        soft_deleted_obj.t_deleted_at = datetime.now(timezone.utc)
        soft_deleted_obj.t_updated_at = datetime.now(timezone.utc)

        # Remove the original object from the session since we don't need it
        session.expunge(self)

        # Add the soft-deleted object to the session
        session.add(soft_deleted_obj)

        # Create diff entry for soft deletion
        diff_entry = DiffEntry(
            entity_type=self.__tablename__,
            t_id=soft_deleted_obj.t_id,
            from_version=self.t_version,
            to_version=self.t_version + 1  # Let before_flush handle final version number
        )
        session.add(diff_entry)

        # Create change record for soft deletion
        diff_change = DiffChange(
            diff_entry=diff_entry,
            operation=ChangeOperation.DELETE,
            field_path='/',  # Root-level operation
            old_value=self._serialize_value(previous_state),
            new_value=None,
            value_type='dict'
        )
        session.add(diff_change)

    def get_change_history(self) -> List[Dict[str, Any]]:
        """Get the complete change history for this entity"""
        history = []
        for diff_entry in self.diffs:
            entry = {
                'version': diff_entry.to_version,
                'timestamp': diff_entry.created_at,
                'changes': []
            }

            for change in diff_entry.changes:
                entry['changes'].append({
                    'operation': change.operation.value,
                    'field': change.field_path.strip('/'),
                    'old_value': self._deserialize_value(change.old_value, change.value_type),
                    'new_value': self._deserialize_value(change.new_value, change.value_type),
                    'value_type': change.value_type
                })

            history.append(entry)

        return history


# track all records processed
_processed_temporal_records = set()


@event.listens_for(Session, 'before_flush')
def handle_temporal_tracking(session: Session, _flush_context, _instances) -> None:
    """Handle temporal tracking before flush."""

    logger.debug("Before flush triggered - tracking item")
    for obj in session.new | session.dirty | session.deleted:
        if isinstance(obj, TemporalMixin):
            _processed_temporal_records.add((type(obj), obj.generate_t_id(obj.get_business_key_params(obj))))

    # Check new objects
    logger.debug(f"Session new count: {len(session.new)}")
    for obj in session.new:
        try:
            obj_type = type(obj)
            logger.debug(f"New object type: {obj_type}")
        except Exception as e:
            logger.debug(f"Error accessing new object: {e}")
            logger.debug(f"Raw new object: {obj}")

    # Check dirty objects
    logger.debug(f"Session dirty count: {len(session.dirty)}")
    for obj in session.dirty:
        try:
            obj_type = type(obj)
            logger.debug(f"Dirty object type: {obj_type}")
        except Exception as e:
            logger.debug(f"Error accessing dirty object: {e}")
            logger.debug(f"Raw dirty object: {obj}")

    # Check deleted objects
    logger.debug(f"Session deleted count: {len(session.deleted)}")
    for obj in session.deleted:
        try:
            obj_type = type(obj)
            logger.debug(f"Deleted object type: {obj_type}")
        except Exception as e:
            logger.debug(f"Error accessing deleted object: {e}")
            logger.debug(f"Raw deleted object: {obj}")

    # Handle deletes first
    for obj in session.deleted:
        if isinstance(obj, TemporalMixin):
            if not obj.t_is_deleted:
                try:
                    identifier = ', '.join(f"{k}={getattr(obj, k)}" for k in obj.get_business_keys())
                except Exception:
                    identifier = "unknown"
                logger.debug(f"Soft deleting {obj.__class__.__name__}({identifier})")

                session.add(obj)
                obj.soft_delete(session)
                session.expunge(obj)

    # Handle new and dirty objects
    for obj in session.new | session.dirty:
        if isinstance(obj, TemporalMixin):
            identifier = ', '.join(f"{k}={getattr(obj, k)}" for k in obj.get_business_keys())
            new_hash = obj.calculate_content_hash()

            try:
                business_key_filter = obj.build_business_key_filter()
                logger.debug(f"Checking existence with business key filter: {business_key_filter}")

                # Create a new connection with READ COMMITTED isolation level
                with session.get_bind().connect().execution_options(
                        isolation_level="READ COMMITTED"
                ) as conn:
                    # Create a temporary session with this connection
                    temp_session = Session(bind=conn)

                    # Base query with business key filter
                    query = temp_session.query(obj.__class__).filter_by(**business_key_filter)
                    if hasattr(obj.__class__, 't_is_current'):
                        query = query.filter_by(t_is_current=True)

                    # Execute query
                    existing = cast(obj.__class__, query.first())

                    # Close temporary session
                    temp_session.close()

                logger.debug(f"Existence check result: {existing is not None}")

            except Exception as e:
                logger.warning(
                    f"Failed to check business keys for {obj.__class__.__name__}: {str(e)}"
                )
                continue

            if existing:
                if existing.t_is_deleted:
                    if existing.t_content_hash == new_hash:
                        logger.debug(
                            f"Found soft-deleted {obj.__class__.__name__}({identifier}) "
                            "with matching content. Restoring."
                        )
                        existing.t_is_deleted = False
                        existing.t_deleted_at = None
                        existing.t_updated_at = datetime.now(timezone.utc)
                        session.expunge(obj)
                        logger.debug(f"After expunge - is obj in session: {obj in session}")
                        continue
                else:
                    if existing.t_content_hash == new_hash and (obj.t_is_deleted is None or (existing.t_is_deleted == obj.t_is_deleted)):
                        logger.debug(
                            f"Found existing {obj.__class__.__name__}({identifier}) "
                            "with matching content. Skipping insert."
                        )
                        session.expunge(obj)
                        continue
                    else:
                        logger.debug(
                            f"Found existing {obj.__class__.__name__}({identifier}) "
                            "with different content. Creating new version."
                        )
                        # Mark existing version as not current
                        existing.t_is_current = False
                        existing.t_updated_at = datetime.now(timezone.utc)

                        # Setup new version
                        obj.t_id = existing.t_id
                        obj.t_version = existing.t_version + 1
                        obj.t_is_current = True if obj.t_is_deleted is None else False
                        obj.t_content_hash = new_hash
                        obj.t_is_deleted = obj.t_is_deleted  if obj.t_is_deleted is not None else False

                        # Control operation order through add sequence
                        session.expunge(obj)
                        session.add(existing)  # Add old version first to update t_is_current = False
                        session.add(obj)

                        # Calculate and record changes
                        changes = obj.calculate_changes(existing)
                        if changes:
                            logger.debug(
                                f"Recording {len(changes)} changes for "
                                f"{obj.__class__.__name__}({identifier})"
                            )
                            diff_entry = DiffEntry(
                                entity_type=obj.__tablename__,
                                t_id=obj.t_id,
                                from_version=existing.t_version,
                                to_version=obj.t_version
                            )
                            session.add(diff_entry)

                            for change in changes:
                                diff_change = DiffChange(
                                    operation=change['operation'],
                                    field_path=change['field_path'],
                                    old_value=change['old_value'],
                                    new_value=change['new_value'],
                                    value_type=change['value_type']
                                )
                                diff_entry.changes.append(diff_change)

                        logger.debug(f"After changes - obj version: {obj.t_version}")
                        logger.debug(f"After changes - is obj in session: {obj in session}")
                        continue

            # Handle updates to existing records
            if hasattr(obj, 't_content_hash') and obj.t_content_hash != new_hash:
                logger.debug(
                    f"Content hash changed for {obj.__class__.__name__}({identifier}): "
                    f"{obj.t_content_hash} -> {new_hash}"
                )
                # Find the current version
                previous: Optional[TemporalMixin] = session.query(obj.__class__).filter_by(
                    t_id=obj.t_id,
                    t_is_current=True
                ).first()

                if previous:
                    logger.debug(
                        f"Creating new version for {obj.__class__.__name__}({identifier}) "
                        f"from v{previous.t_version}"
                    )
                    # Update previous version
                    previous.t_is_current = False
                    previous.t_updated_at = datetime.now(timezone.utc)

                    # Calculate changes between versions
                    changes = obj.calculate_changes(previous)

                    if changes:
                        logger.debug(
                            f"Recording {len(changes)} changes for "
                            f"{obj.__class__.__name__}({identifier})"
                        )
                        diff_entry = DiffEntry(
                            entity_type=obj.__tablename__,
                            t_id=obj.t_id,
                            from_version=previous.t_version,
                            to_version=previous.t_version + 1
                        )
                        session.add(diff_entry)

                        for change in changes:
                            diff_change = DiffChange(
                                diff_entry_id=diff_entry.id,
                                operation=change['operation'],
                                field_path=change['field_path'],
                                old_value=change['old_value'],
                                new_value=change['new_value'],
                                value_type=change['value_type']
                            )
                            session.add(diff_change)

                    # Update version number
                    obj.t_version = previous.t_version + 1
                    logger.debug(
                        f"Incrementing version for {obj.__class__.__name__}({identifier}) "
                        f"to v{obj.t_version}"
                    )
                else:
                    # No previous version exists, this is first version
                    logger.debug(
                        f"Creating first version for {obj.__class__.__name__}({identifier})"
                    )
                    obj.t_version = 1

                # Update current version
                obj.t_content_hash = new_hash
                obj.t_is_current = True
                obj.t_updated_at = datetime.now(timezone.utc)

            elif not hasattr(obj, 't_content_hash'):
                # Initial hash for new objects
                logger.debug(
                    f"Initializing new {obj.__class__.__name__}({identifier}) "
                    f"with content hash {new_hash}"
                )
                obj.t_content_hash = new_hash
                obj.t_version = 1
                obj.t_is_current = True


@event.listens_for(Session, 'before_commit')
def identify_and_soft_delete_stale_records(session: Session):
    # Group processed t_ids by model
    processed_by_model = {}
    for model, t_id in _processed_temporal_records:
        if model not in processed_by_model:
            processed_by_model[model] = set()
        processed_by_model[model].add(t_id)

    # Process each model with processed records
    for model, processed_t_ids in processed_by_model.items():
        # Find current records not in processed set for this specific model
        stale_records = session.query(model).filter(
            model.t_is_current == True,
            model.t_is_deleted == False,
            model.t_id.notin_(processed_t_ids)
        ).all()

        # Soft delete stale records
        for record in stale_records:
            logger.debug(f"Soft delete record: {record.t_id}")
            record.soft_delete(session)
            # session.expunge(record)

    # Clear the processed records after handling
    _processed_temporal_records.clear()
