from functools import wraps
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

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
        SessionFactory = sessionmaker(bind=engine_or_session_factory)
    else:
        SessionFactory = engine_or_session_factory

    # Create new session
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.debug(e)
        session.rollback()
        raise
    finally:
        session.close()

