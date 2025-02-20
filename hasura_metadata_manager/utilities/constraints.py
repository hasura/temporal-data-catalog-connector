from sqlalchemy import inspect, MetaData
from sqlalchemy.sql.ddl import DropConstraint


def drop_all_fk_constraints(session):
    """Drop all FK constraints in a database-agnostic way"""
    inspector = inspect(session.bind)
    metadata = MetaData()
    metadata.reflect(bind=session.bind)

    for table_name in inspector.get_table_names():
        table = metadata.tables[table_name]
        for fk_constraint in table.foreign_key_constraints:
            drop_ddl = DropConstraint(fk_constraint, cascade=True)
            session.execute(drop_ddl)
