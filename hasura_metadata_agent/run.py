import argparse
import logging
import warnings

from sqlalchemy.exc import SAWarning

warnings.simplefilter("always", SAWarning)
warnings.filterwarnings("ignore", message=".*not matching locally specified columns.*")

from hasura_metadata_manager.load import init_with_session


def configure_logging(level):
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    logging.basicConfig(level=numeric_level)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-cli-level", help="Set the log level", type=str, default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_cli_level)

    init_with_session()
