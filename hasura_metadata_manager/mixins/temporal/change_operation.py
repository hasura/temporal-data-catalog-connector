import enum


class ChangeOperation(enum.Enum):
    """Enumeration of possible change operations in temporal tracking"""

    ADD = 'add'  # A new field was added
    REMOVE = 'remove'  # A field was removed
    REPLACE = 'replace'  # A field's value was changed
    DELETE = 'delete'  # The entire record was soft-deleted
    RESTORE = 'restore'  # A soft-deleted record was restored
