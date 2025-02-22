import os
import warnings
from datetime import datetime, timezone
from typing import cast

from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker

from . import Supergraph
from .generate_relationship_indices import apply_indices, apply_constraints
from .utilities import SchemaHelper, drop_all_fk_constraints
from .utilities import managed_session  # Assuming these exist

logger = __import__("logging").getLogger(__name__)


def database_exists(url):
    session = None
    engine = None
    try:
        engine = create_engine(url)
        session_factory = sessionmaker(bind=engine)
        session = session_factory()
        session.query(Supergraph).first()
        return True
    except (exc.OperationalError, exc.ProgrammingError):
        return False
    finally:
        if session is not None:
            session.close()
        if engine is not None:
            engine.dispose()



def create_engine_config(database_url: str):
    """Create engine with standard configuration."""
    connect_args = {
        'connect_timeout': int(os.getenv('CONNECT_TIMEOUT', 60)),
    }
    keepalives = int(os.getenv('KEEPALIVES', -1))
    if keepalives > 0:
        connect_args['keepalives'] = keepalives
    keepalives_idle = int(os.getenv('KEEPALIVES_IDLE', -1))
    if keepalives_idle > 0:
        connect_args['keepalives_idle'] = keepalives_idle
    keepalives_interval = int(os.getenv('KEEPALIVES_INTERNAL', -1))
    if keepalives_interval > 0:
        connect_args['keepalives_interval'] = keepalives_interval
    keepalives_count = int(os.getenv('KEEPALIVES_COUNT', -1))
    if keepalives_count > 0:
        connect_args['keepalives_count'] = keepalives_count

    return create_engine(
        database_url,
        pool_pre_ping=os.getenv('POOL_PRE_PING', 'true').lower() in ['true', '1', 't', 'yes', ''],
        pool_size=int(os.getenv('POOL_SIZE', '50')),
        max_overflow=int(os.getenv('MAX_OVERFLOW', '30')),
        connect_args=connect_args
    )


def init_schema_from_build(
        database_url: str,
        clean_database=True,
        engine_build: str = './example/engine/build/metadata.json'):
    # Capture and logger.debug warnings
    with warnings.catch_warnings():
        # Cause all warnings to always be triggered
        warnings.simplefilter("always")

        try:
            engine = create_engine_config(database_url)

            # Do cleanup in its own connection if needed
            if clean_database or not database_exists(database_url):
                with managed_session(engine) as session:
                    importer = SchemaHelper(session)
                    importer.cleanup_database_with_cascade()
            else:
                with managed_session(engine) as session:
                    drop_all_fk_constraints(session)
        finally:
            engine.dispose()

        # Create fresh engine for schema import
        engine = create_engine_config(database_url)
        try:
            with managed_session(engine) as session:
                importer = SchemaHelper(session)

                existing_supergraph = cast(Supergraph, session.query(Supergraph).filter_by(
                    t_is_current=True,
                    t_is_deleted=False
                ).first())

                # Version checking logic
                if not clean_database and existing_supergraph is not None:

                    Supergraph.set_initialization_timestamp(existing_supergraph.t_created_at)
                    # Get modification time in seconds since the epoch
                    mod_time = os.path.getmtime(engine_build)

                    # Convert to a datetime object in UTC
                    timestamp = datetime.fromtimestamp(mod_time, tz=timezone.utc)

                    if existing_supergraph:
                        if existing_supergraph.version == "v2":
                            if existing_supergraph.t_updated_at.replace(tzinfo=timezone.utc) >= timestamp:
                                logger.debug(f"No changes detected in {engine_build}. Skipping schema import.")
                                return
                        else:
                            logger.debug(
                                f"Existing supergraph has version {existing_supergraph.version}." 
                                "Skipping schema import.")
                            return
                    else:
                        logger.debug(f"No existing supergraph found. Importing schema from {engine_build}.")

                supergraph = importer.import_file(engine_build)
                assert supergraph.name == "default"
                assert supergraph.version == "v2"

            # Register temporal views after schema is loaded
            from .mixins.temporal import register_temporal_views
            from .base.core_base import CoreBase
            from .base.base import Base

            # register_temporal_views(CoreBase, engine=engine)
            apply_indices(Base, engine=engine)
            apply_constraints(Base, engine=engine)
        finally:
            engine.dispose()


def init_with_session(clean_database=False):
    """Initialize schema with environment configuration and proper resource cleanup."""
    clean_database = os.getenv('CLEAN_DATABASE', str(clean_database)).lower() in ['true', '1', 't', 'yes', 'y']
    engine_build = os.getenv('ENGINE_BUILD_PATH', './example/engine/build/metadata.json')
    database_url = os.getenv('DATABASE_URL', '')

    logger.info(f"Engine build path: {engine_build}")
    logger.info(f"Database URL: {database_url}")
    logger.info(f"Clean Database: {clean_database}")

    init_schema_from_build(
        database_url=database_url,
        clean_database=clean_database,
        engine_build=engine_build
    )
