import warnings

from sqlalchemy.exc import SAWarning

warnings.simplefilter("always", SAWarning)
warnings.filterwarnings("ignore", message=".*not matching locally specified columns.*")

# Import the init_with_session function from load.py
from app.metadata.load import init_with_session

# Run the init_with_session function by default when this module is executed
if __name__ == "__main__":
    init_with_session()  # Default call with no arguments (clean_database=False unless overridden by an ENV variable)
