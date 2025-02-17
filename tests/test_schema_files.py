import warnings
from typing import TYPE_CHECKING

import pytest

from ..utilities.compare_json_files import compare_json_files

if TYPE_CHECKING:
    pass

# Tell pytest to show warnings
pytestmark = pytest.mark.filterwarnings("always")


def test_schema_files():
    # Capture and print warnings
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered
        warnings.simplefilter("always")

        # Compare files
        is_equal, differences = compare_json_files('./example/engine/build/metadata.json', 'supergraph.json', [
            "kind;definition.sourceType;definition.name",
            "kind;definition.name",
            "kind;definition.modelName",
            "kind;definition.typeName",
            "kind;definition.dataConnectorScalarType",
            "name", "id", "key"
        ])
        print(f"Files are equivalent: {is_equal}")
        if not is_equal:
            print("Differences found:")
            for diff in differences:
                print(f"- {diff}")

        # Print any warnings that were captured
        if len(w) > 0:
            print("\nWarnings during test:")
            for warning in w:
                print(f"Warning: {warning.message}")
