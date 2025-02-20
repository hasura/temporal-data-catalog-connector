from typing import List, Set, Type, Any, Tuple

from sqlalchemy import Column, ForeignKeyConstraint, Index, UniqueConstraint, select, func, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.sql.ddl import AddConstraint
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from hasura_metadata_manager.mixins.rdf.instance_rdf_mixin import logger


def parse_join_condition(condition: Any) -> List[Tuple[Column, Column]]:
    if isinstance(condition, BooleanClauseList):
        return [col for clause in condition.clauses for col in parse_join_condition(clause)]

    if isinstance(condition, BinaryExpression):
        left = getattr(condition.left, 'element', condition.left)
        right = getattr(condition.right, 'element', condition.right)

        if isinstance(left, Column) and isinstance(right, Column):
            return [(left, right)]

    return []


def generate_index_name(table_name: str, column_keys: List[str], max_length: int = 63) -> str:
    """Generate a PostgreSQL-compatible index name."""
    import hashlib

    # Create base name
    base_name = f"ix_{table_name}_{'_'.join(column_keys)}"

    if len(base_name) <= max_length:
        return base_name

    # Generate hash of full name
    name_hash = hashlib.sha256(base_name.encode()).hexdigest()[:10]

    # Reserve characters for the hash and prefix
    available_space = max_length - len(name_hash) - len("ix__") - 1
    truncated_name = f"ix_{table_name[:available_space]}"

    return f"{truncated_name}_{name_hash}"


def generate_relationship_indices(base: Type[Any]) -> List[Index]:
    indices: List[Index] = []
    processed_tables: Set[str] = set()

    for mapper in base.registry.mappers:
        if not hasattr(mapper.class_, '__table__'):
            continue

        table = mapper.class_.__table__

        for relationship in mapper.relationships:
            if not isinstance(relationship, RelationshipProperty):
                continue

            if relationship.primaryjoin is None:
                continue

            join_columns = parse_join_condition(relationship.primaryjoin)
            foreign_columns = []
            for local_col, remote_col in join_columns:
                if local_col.table == table:
                    foreign_columns.append(local_col)
                elif remote_col.table == table:
                    foreign_columns.append(remote_col)

            if foreign_columns:
                idx_name = generate_index_name(
                    table.name,
                    [col.key for col in foreign_columns]
                )
                if idx_name not in processed_tables:
                    indices.append(Index(idx_name, *foreign_columns))
                    processed_tables.add(idx_name)

    return indices


def is_primary_key_column(column: Column) -> bool:
    """Check if a column is part of the primary key."""
    return column.primary_key


def generate_relationship_constraints(base: Type[Any]) -> List[Tuple[str, ForeignKeyConstraint]]:
    constraints: List[Tuple[str, ForeignKeyConstraint]] = []
    processed_constraints: Set[str] = set()

    for mapper in base.registry.mappers:
        if not hasattr(mapper.class_, '__table__'):
            continue

        table = mapper.class_.__table__

        for relationship in mapper.relationships:
            # Skip relationships with info={'skip_constraint': True} as they indicate one-to-many relationships
            if relationship.info.get('skip_constraint'):
                continue

            if relationship.primaryjoin is None:
                continue

            remote_table = relationship.mapper.class_.__table__
            remote_pk_cols = set(col.name for col in remote_table.primary_key if col.name != 't_version')

            column_pairs = parse_join_condition(relationship.primaryjoin)
            if not column_pairs:
                continue

            valid_pairs = [(local_col, remote_col) for local_col, remote_col in column_pairs
                           if remote_col.name in remote_pk_cols]

            if not valid_pairs:
                continue

            # Add t_is_current from both tables
            try:
                local_current = table.columns['t_is_current']
                remote_current = remote_table.columns['t_is_current']
                valid_pairs.append((local_current, remote_current))
            except Exception as e:
                logger.debug(f"Could not add t_is_current columns: {str(e)}")
                continue

            local_cols = []
            remote_cols = []

            for local_col, remote_col in valid_pairs:
                # Ensure we're adding columns from the correct table
                if local_col.table == table:
                    local_cols.append(local_col)
                    remote_cols.append(f"{remote_col.table.name}.{remote_col.key}")
                elif remote_col.table == table:
                    local_cols.append(remote_col)
                    remote_cols.append(f"{local_col.table.name}.{local_col.key}")

            if not local_cols or not remote_cols:
                continue

            constraint_name = generate_constraint_name(
                "fk",
                table.name,
                [col.key for col in local_cols]
            )

            if constraint_name in processed_constraints:
                continue

            try:
                fk_constraint = ForeignKeyConstraint(
                    local_cols,
                    remote_cols,
                    name=constraint_name,
                    use_alter=True,  # Handle circular dependencies
                    deferrable=True,
                    initially='DEFERRED',
                    onupdate='CASCADE',
                    ondelete='SET NULL'
                )

                # Ensure all local columns are nullable except t_is_current
                for col in local_cols:
                    if col.name != 't_is_current':
                        col.nullable = True

                constraints.append((table.name, fk_constraint))
                processed_constraints.add(constraint_name)

            except Exception as e:
                logger.debug(f"Failed to create constraint {constraint_name}: {str(e)}")
                continue

    return constraints


def apply_indices(base: Type[Any], engine: Any) -> None:
    indices = generate_relationship_indices(base)

    for index in indices:
        # Drop operation in its own transaction
        with engine.connect() as conn:
            with conn.begin():
                try:
                    index.drop(bind=conn)
                    print(f"Dropped existing index: {index.name}")
                except Exception as drop_e:
                    print(f"[DEBUG] Error dropping the index {index.name}. Details: {str(drop_e)}")
                    if "does not exist" not in str(drop_e).lower():
                        print(f"[WARNING] Unable to drop index: {index.name}. Skipping...")
                        continue

        # Create operation in fresh transaction
        with engine.connect() as conn:
            with conn.begin():
                try:
                    index.create(bind=conn)
                    print(f"Successfully created/recreated index: {index.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to create/recreate index {index.name}. Reason: {str(e)}")
                    continue


def generate_constraint_name(prefix: str, table_name: str, column_names: List[str], max_length: int = 63) -> str:
    """Generate a database-compatible constraint name."""
    import hashlib

    base_name = f"{prefix}_{table_name}_{'_'.join(column_names)}"

    if len(base_name) <= max_length:
        return base_name

    name_hash = hashlib.sha256(base_name.encode()).hexdigest()[:10]
    available_space = max_length - len(name_hash) - len(f"{prefix}__") - 1
    truncated_name = f"{prefix}_{table_name[:available_space]}"

    return f"{truncated_name}_{name_hash}"


def ensure_unique_constraint(table, columns, engine):
    """Ensure a unique constraint exists on the specified columns."""
    # Add t_version if not already in columns
    modified_columns = list(columns)
    if not any(col.name == 't_version' for col in modified_columns):
        modified_columns.append(table.c.t_version)

    constraint_name = generate_constraint_name(
        "uq",
        table.name,
        [col.name for col in modified_columns]
    )

    print(f"[DEBUG] Creating unique constraint {constraint_name} on {table.name}")
    print(f"[DEBUG] Columns: {[col.name for col in modified_columns]}")

    unique_constraint = UniqueConstraint(*modified_columns, name=constraint_name)

    # Create constraint - separate connection
    try:
        with engine.connect().execution_options(timeout=30) as conn:
            with conn.begin():
                conn.execute(AddConstraint(unique_constraint))
                print(f"Added unique constraint: {constraint_name} to table {table.name}")
                return
    except IntegrityError as e:
        if "already exists" in str(e).lower():
            print(f"Constraint '{constraint_name}' already exists. Skipping.")
            return

        # Check for duplicates - new connection
        with engine.connect().execution_options(timeout=30) as check_conn:
            with check_conn.begin():
                # Create the query using column references
                column_refs = [column.label(column.name) for column in modified_columns]
                duplicates_query = select(
                    *column_refs,
                    func.count().label('duplicate_count')
                ).select_from(table).group_by(
                    *modified_columns
                ).having(func.count() > 1)

                result = check_conn.execute(duplicates_query)
                duplicates = []

                for row in result:
                    # Convert row to dict safely using _mapping
                    row_dict = row._mapping
                    duplicate = {
                        col.name: row_dict[col.name]
                        for col in modified_columns
                    }
                    duplicate['count'] = row_dict['duplicate_count']
                    duplicates.append(duplicate)

                if duplicates:
                    duplicate_details = "\n".join(
                        [str(dup) for dup in duplicates]
                    )
                    raise Exception(
                        f"Could not add unique constraint {constraint_name} to table {table.name} "
                        f"due to duplicate rows:\n{duplicate_details}"
                    )
                else:
                    raise Exception(f"Failed to add constraint but no duplicates found. Original error: {str(e)}")


def check_db_for_constraint(table, columns, engine):
    """Check database for existing unique constraints in a database-agnostic way."""
    constraint_name = generate_constraint_name(
        "uq",
        table.name,
        [col.name for col in columns]
    )

    inspector = inspect(engine)
    unique_constraints = inspector.get_unique_constraints(table.name)

    # Check both name and column composition
    for uc in unique_constraints:
        if uc['name'] == constraint_name:
            print(f"[DEBUG] Found constraint by name: {constraint_name}")
            return True

        # Also check column composition in case name is different
        if set(uc['column_names']) == {col.name for col in columns}:
            print(f"[DEBUG] Found constraint by columns: {uc['name']}")
            return True

    return False


def needs_unique_constraint(table, columns, engine):
    """Check if columns need a unique constraint by checking both hasura_metadata_manager and database."""
    column_names = set(col.name for col in columns)
    print(f"[DEBUG] Checking columns: {column_names} on table {table.name}")

    # First check database
    if check_db_for_constraint(table, columns, engine):
        print(f"[DEBUG] Found existing constraint in database for {table.name}")
        return False

    # Then check hasura_metadata_manager for completeness
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            constraint_col_names = set(col.name for col in constraint.columns)
            if column_names == constraint_col_names:
                print(f"[DEBUG] Found matching constraint in hasura_metadata_manager: {constraint.name}")
                return False

    print(f"[DEBUG] No matching unique constraint found for {table.name}")
    return True


def apply_constraints(base: Type[Any], engine: Any) -> None:
    """Generate and apply foreign key constraints to the database."""
    constraints = generate_relationship_constraints(base)

    for table_name, constraint in constraints:
        try:
            # Check and create unique constraints if needed - separate connection
            for mapper in base.registry.mappers:
                mapped_class = mapper.class_
                if hasattr(mapped_class, '__table__') and mapped_class.__table__.name == table_name:
                    # Get referenced columns
                    referenced_table = constraint.elements[0].column.table
                    referenced_cols = [elem.column for elem in constraint.elements]

                    if needs_unique_constraint(referenced_table, referenced_cols, engine):
                        # Use separate connection for unique constraint
                        # with engine.connect().execution_options(timeout=30) as unique_conn:
                        ensure_unique_constraint(referenced_table, referenced_cols, engine)

                    # Add constraint to hasura_metadata_manager
                    mapped_class.__table__.append_constraint(constraint)
                    print(f"Added constraint to hasura_metadata_manager: {constraint.name} on table {table_name}")

                    # Create FK constraint - separate connection
                    with engine.connect().execution_options(timeout=30) as fk_conn:
                        with fk_conn.begin():
                            fk_conn.execute(AddConstraint(constraint))
                            print(f"Added constraint to database: {constraint.name} on table {table_name}")
                    break

        except Exception as e:
            print(f"Failed to add constraint {constraint.name}: {str(e)}")
            continue


def remove_relationship_constraints(base: Type[Any]) -> None:
    """
    Remove all foreign key constraints that were generated based on relationships.
    This function will remove constraints by modifying table hasura_metadata_manager.

    Args:
        base: SQLAlchemy declarative base class
    """
    for mapper in base.registry.mappers:
        mapped_class = mapper.class_
        if not hasattr(mapped_class, '__table__'):
            continue

        table = mapped_class.__table__
        constraints_to_remove = [
            constraint for constraint in table.constraints
            if isinstance(constraint, ForeignKeyConstraint)
               and constraint.name
               and constraint.name.startswith('fk_')
        ]

        # Remove constraints from table hasura_metadata_manager
        for constraint in constraints_to_remove:
            table.constraints.remove(constraint)
            print(f"Removed constraint: {constraint.name} from table {table.name}")


# Example usage:
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

Base = declarative_base()
engine = create_engine('postgresql://user:password@localhost/dbname')

# Generate and apply both indices and constraints
apply_indices(Base, engine)
apply_constraints(Base)

# Or just generate them for migration scripts
indices = generate_relationship_indices(Base)
constraints = generate_relationship_constraints(Base)

# To remove all constraints:
remove_relationship_constraints(Base)
"""
