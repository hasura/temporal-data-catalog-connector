from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker, Session

logger = __import__("logging").getLogger(__name__)

@contextmanager
def managed_session(engine_or_session_factory):
    """
    Session management context manager with proper transaction handling.

    Args:
        engine_or_session_factory: Either an SQLAlchemy Engine or sessionmaker instance
    """
    if isinstance(engine_or_session_factory, Session):
        # If already a session, just yield it
        yield engine_or_session_factory
        return

    # Create SessionFactory if given an engine
    if not isinstance(engine_or_session_factory, sessionmaker):
        session_factory = sessionmaker(bind=engine_or_session_factory)
    else:
        session_factory = engine_or_session_factory

    # Create new session
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.debug(e)
        session.rollback()
        raise
    finally:
        session.close()

