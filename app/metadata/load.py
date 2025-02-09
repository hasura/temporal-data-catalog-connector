import os
import warnings
from datetime import datetime
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import Supergraph
from .generate_relationship_indices import apply_indices, apply_constraints
from .utilities import SchemaHelper
from .utilities import managed_session, transactional  # Assuming these exist
logger = __import__("logging").getLogger(__name__)


def create_engine_config(database_url: str):
    """Create engine with standard configuration."""
    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800
    )


def init_schema_from_build(session, clean_database=True,
                           engine_build: str = './example/engine/build/metadata.json'):  # Add flag to control cleanup
    # Capture and logger.debug warnings
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered
        warnings.simplefilter("always")

        importer = SchemaHelper(session)

        # Only cleanup if flag is set
        if clean_database:
            importer.cleanup_database_with_cascade()

        else:
            existing_supergraph = cast(Supergraph, session.query(Supergraph).filter_by(t_is_current=True,
                                                                                       t_is_deleted=False).first())
            timestamp = datetime.fromtimestamp(os.path.getmtime(engine_build))
            if existing_supergraph:
                if existing_supergraph.version == "v2":
                    if existing_supergraph.t_updated_at >= timestamp:
                        logger.debug(f"No changes detected in {engine_build}. Skipping schema import.")
                        return
                else:
                    logger.debug(f"Existing supergraph has version {existing_supergraph.version}. Skipping schema import.")
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

        register_temporal_views(CoreBase, engine=importer.engine)
        apply_indices(Base, engine=importer.engine)
        apply_constraints(Base, engine=importer.engine)


def init_with_session(clean_database=False):
    """Initialize schema with environment configuration and proper resource cleanup."""
    clean_database = os.getenv('CLEAN_DATABASE', str(clean_database)).lower() in ['true', '1', 't', 'yes', 'y']
    engine_build = os.getenv('ENGINE_BUILD_PATH', './example/engine/build/metadata.json')
    database_url = os.getenv('DATABASE_URL',
                             "postgresql://kenstott:rN8qOh6AEMCP@ep-yellow-salad-961725.us-west-2.aws.neon.tech/hasura_config?sslmode=require")

    logger.info(f"Engine build path: {engine_build}")
    logger.info(f"Database URL: {database_url}")
    logger.info(f"Clean Database: {clean_database}")

    engine = create_engine_config(database_url)
    # SessionFactory = sessionmaker(bind=engine)

    try:
        with managed_session(engine) as session:
            init_schema_from_build(
                session=session,
                clean_database=clean_database,
                engine_build=engine_build
            )
    finally:
        engine.dispose()
