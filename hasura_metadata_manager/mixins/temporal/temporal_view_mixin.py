import logging

from sqlalchemy import inspect, event, DDL, text
from sqlalchemy.ext.declarative import declared_attr

logger = logging.getLogger(__name__)


class TemporalViewMixin:
    """
    Mixin that automatically creates a view for the current state of a temporal table.
    Should be used in conjunction with TemporalMixin.

    Creates a view that shows only active (non-deleted) current records,
    excluding all temporal tracking columns (t_*).
    """

    @declared_attr
    def __current_view_name__(cls) -> str:
        """Generate the view name for current state"""
        table_name = getattr(cls, '__tablename__', cls.__name__.lower())
        return f"current_{table_name}"

    @classmethod
    def get_view_table_name(cls) -> str:
        """Get the actual table name of the model"""
        return getattr(cls, '__tablename__', cls.__name__.lower())

    @classmethod
    def create_current_view(cls) -> str:
        """Generate the SELECT statement for the current view"""
        # Get all columns except temporal tracking ones through the mapper
        mapper = inspect(cls)
        columns = [col.name for col in mapper.columns if not col.name.startswith('t_')]

        # Build column list for SELECT
        column_list = ', '.join(f'"{col}"' for col in columns)

        # Quote the table name to handle reserved words
        table_name = f'"{cls.get_view_table_name()}"'

        view_query = f"""
            SELECT {column_list}
            FROM {table_name}
            WHERE t_is_current = true 
            AND t_is_deleted = false
        """

        logger.debug(f"Generated view query for {cls.__name__}: {view_query}")
        return view_query

    @classmethod
    def create_view_ddl(cls, dialect_name: str) -> str:
        """Generate database-specific DDL for view creation."""
        base_query = cls.create_current_view()
        view_name = f'"{getattr(cls, "__current_view_name__")}"'

        if dialect_name == 'sqlite':
            # SQLite doesn't support CREATE OR REPLACE
            ddl = f"""
                DROP VIEW IF EXISTS {view_name};
                CREATE VIEW {view_name} AS {base_query}
            """
        elif dialect_name == 'postgresql':
            ddl = f"CREATE OR REPLACE VIEW {view_name} AS {base_query}"
        elif dialect_name == 'mysql':
            ddl = f"CREATE OR REPLACE VIEW {view_name} AS {base_query}"
        elif dialect_name == 'oracle':
            ddl = f"CREATE OR REPLACE FORCE VIEW {view_name} AS {base_query}"
        elif dialect_name == 'mssql':
            # For MSSQL, use square brackets instead of double quotes
            view_name = view_name.replace('"', ']').replace('"', '[')
            ddl = f"""
                IF OBJECT_ID('{view_name}', 'V') IS NOT NULL
                    DROP VIEW {view_name};
                GO
                CREATE VIEW {view_name} AS {base_query}
            """
        else:
            logger.warning(
                f"Dialect '{dialect_name}' not explicitly supported for view creation. "
                "Falling back to standard SQL syntax."
            )
            # Use the safest approach for unknown dialects
            ddl = f"""
                DROP VIEW IF EXISTS {view_name};
                CREATE VIEW {view_name} AS {base_query}
            """

        logger.debug(f"Generated DDL for {cls.__name__}: {ddl}")
        return ddl

    @classmethod
    def register_current_view(cls, engine):
        """Register and immediately create the view"""
        try:
            # Get the table through inspection
            mapper = inspect(cls)
            table = mapper.local_table
        except Exception as e:
            raise AttributeError(
                f"Class {cls.__name__} is not properly mapped to a table. Error: {str(e)}")

        if table is None:
            raise AttributeError(
                f"Class {cls.__name__} has no table mapping. Ensure the model is properly configured.")

        create_ddl = cls.create_view_ddl(engine.dialect.name)

        logger.info(f"Creating view for {cls.__name__}")
        logger.debug(f"DDL: {create_ddl}")

        try:
            # Execute the DDL
            with engine.begin() as conn:
                # For SQLite and other dialects that might use multiple statements
                for statement in create_ddl.split(';'):
                    if statement.strip():
                        conn.execute(text(statement))
                logger.info(f"Successfully created view for {cls.__name__}")

            # Register event listeners for future operations
            event.listen(table, 'after_create', DDL(create_ddl))
        except Exception as e:
            logger.error(f"Error creating view for {cls.__name__}: {str(e)}")
            raise

    @classmethod
    def drop_view_ddl(cls, dialect_name: str) -> str:
        """
        Generate database-specific DDL for view dropping.
        Falls back to standard SQL if dialect is unknown.
        """
        view_name = getattr(cls, '__current_view_name__')

        if dialect_name == 'mssql':
            return f"IF OBJECT_ID('{view_name}', 'V') IS NOT NULL DROP VIEW {view_name}"
        else:
            if dialect_name not in ('postgresql', 'mysql', 'oracle'):
                logger.warning(
                    f"Dialect '{dialect_name}' not explicitly supported for view dropping. "
                    "Falling back to standard SQL syntax. This may fail for some databases."
                )
            return f"DROP VIEW IF EXISTS {view_name}"


def register_temporal_views(base_class, engine):
    """Register current state views for all temporal tables.

    Args:
        base_class: SQLAlchemy declarative base class
        engine: SQLAlchemy engine instance
    """
    from . import TemporalMixin

    registry = base_class.registry
    for mapper in registry.mappers:
        class_ = mapper.class_
        if issubclass(class_, TemporalMixin) and class_ != TemporalMixin:
            if hasattr(class_, 'register_current_view'):
                logger.info(f"Registering current view for {class_.__name__}")
                class_.register_current_view(engine)
            else:
                logger.warning(
                    f"Class {class_.__name__} has TemporalMixin but not TemporalViewMixin. "
                    "Skipping view creation."
                )


# Example usage:
"""
# 1. Define your temporal model with both mixins
class User(TemporalMixin, TemporalViewMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)

# 2. Either register views individually:
User.register_current_view(engine)

# 3. Or register all temporal views at once:
register_temporal_views(Base, engine)

# 4. The view can then be queried in SQL:
SELECT * FROM current_users;
"""
