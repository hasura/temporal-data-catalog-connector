from functools import wraps

logger = __import__("logging").getLogger(__name__)

def transactional(func):
    """Decorator for methods requiring transaction management"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        session = kwargs.get('session')
        if session is None:
            raise ValueError("Session required for transactional operations")

        try:
            with session.begin_nested():
                result = func(*args, **kwargs)
                return result
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction failed in {func.__name__}: {str(e)}")
            raise

    return wrapper
