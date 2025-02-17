import itertools
import json
from collections.abc import Mapping, Sequence
from typing import List, Any, Tuple


def compare_json_files(file1_path: str, file2_path: str, unique_key_candidates: List[str] = None) -> Tuple[
    bool, List[str]]:
    """
    Compare two JSON files for equivalence, ignoring key and array order.

    Args:
        file1_path (str): Path to first JSON file.
        file2_path (str): Path to second JSON file.
        unique_key_candidates (List[str], optional): List of key candidates (or paths to keys, or composite keys)
                                                    to consider for unique identification of objects within arrays.
                                                    Defaults to ["name", "id", "key"].

    Returns:
        Tuple[bool, List[str]]: (is_equivalent, list of differences)
        The differences list contains paths and descriptions of inequivalencies
    """
    try:
        with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
            json1 = json.load(f1)
            json2 = json.load(f2)

        if unique_key_candidates is None:
            unique_key_candidates = ["name", "id", "key"]

        differences = []
        is_equivalent = compare_objects(json1, json2, "", differences, unique_key_candidates)
        return is_equivalent, differences

    except Exception as e:
        return False, [f"Error reading or parsing JSON files: {str(e)}"]


def get_value_by_path(obj: Any, path: str) -> Any:
    """
    Helper function to retrieve a value (or composite value) from a nested object
    using a path string (or composite path string).
    """
    try:
        if ";" in path:  # Check for composite path
            values = []
            for key_part in path.split(";"):
                value = obj
                for key in key_part.split("."):
                    value = value[key]
                values.append(str(value))  # Convert to string before joining
            return ";".join(values)  # Return composite value as string
        else:  # Single path
            for key in path.split("."):
                obj = obj[key]
            return obj
    except (KeyError, TypeError):
        return None


def compare_objects(obj1: Any, obj2: Any, path: str, differences: List[str], unique_key_candidates: List[str]) -> bool:
    """
    Recursively compare two JSON objects and collect differences.

    Args:
        obj1: First object to compare.
        obj2: Second object to compare.
        path: Current JSON path being compared.
        differences: List to collect difference descriptions.
        unique_key_candidates: List of key candidates (or paths to keys, or composite keys)
                               to consider for unique identification.

    Returns:
        bool: True if objects are equivalent, False otherwise.
    """
    # Check if types match
    if type(obj1) != type(obj2):
        differences.append(f"Type mismatch at {path}: {type(obj1).__name__} vs {type(obj2).__name__}")
        return False

    # Handle dictionaries
    if isinstance(obj1, Mapping):
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())

        is_equivalent = True  # Initialize is_equivalent to True

        # Check for missing/extra keys
        if keys1 != keys2:
            is_equivalent = False  # Set to False if key differences are found

            missing = keys1 - keys2
            extra = keys2 - keys1
            if missing:
                differences.append(f"Missing keys at {path}: {sorted(missing)}")
            if extra:
                differences.append(f"Extra keys at {path}: {sorted(extra)}")

        # Recursively compare values
        for key in keys1 & keys2:  # Use the intersection of keys
            if isinstance(key, str):
                current_path = f"{path}.{key}" if path else key
                if not compare_objects(obj1[key], obj2[key], current_path, differences, unique_key_candidates):
                    is_equivalent = False
            else:
                differences.append(f"ERROR: Non-string key encountered at {path}: {key}")
        return is_equivalent

    # Handle arrays
    elif isinstance(obj1, Sequence) and not isinstance(obj1, (str, bytes)):
        if len(obj1) != len(obj2):
            differences.append(f"Array length mismatch at {path}: {len(obj1)} vs {len(obj2)}")

        # Check if ALL elements are objects and EVERY object has at least one candidate key
        all_objects = all(isinstance(item, Mapping) for item in itertools.chain(obj1, obj2))
        all_have_keys = all(
            any(get_value_by_path(item, key) is not None for key in unique_key_candidates)
            for item in itertools.chain(obj1, obj2) if isinstance(item, Mapping)
        )

        if all_objects and all_have_keys:
            # --- Record unique keys for each object (simplified)
            keys1 = {}
            keys2 = {}

            for i, item in enumerate(obj1):
                for key in unique_key_candidates:
                    if get_value_by_path(item, key) is not None:
                        keys1[i] = (key, get_value_by_path(item, key))
                        break

            for i, item in enumerate(obj2):
                for key in unique_key_candidates:
                    if get_value_by_path(item, key) is not None:
                        keys2[i] = (key, get_value_by_path(item, key))
                        break

            # --- Comparison logic using recorded keys
            if set(keys1.values()) != set(keys2.values()):
                # Example:
                missing = set(keys1.values()) - set(keys2.values())
                extra = set(keys2.values()) - set(keys1.values())
                if missing:
                    differences.append(f"Missing array elements at {path} with keys: {sorted(missing)}")
                if extra:
                    differences.append(f"Extra array elements at {path} with keys: {sorted(extra)}")

            # Compare corresponding objects (modified)
            for i, (key, value) in keys1.items():
                found_match = False
                for j, (key2, value2) in keys2.items():
                    if key == key2 and value == value2:  # Match found
                        temp_diff = []
                        current_path = f"{path}[{i}]" if path else f"[{i}]"

                        # --- Compare the objects recursively (without hardcoding key names)
                        if not compare_objects(obj1[i], obj2[j], current_path, temp_diff, unique_key_candidates):
                            differences.extend(
                                [f"{current_path} (key: {key}, value: {value}): {diff}" for diff in temp_diff])

                        found_match = True
                        break
                if not found_match:
                    differences.append(
                        f"No matching array element found at {path}[{i}] for key '{key}' with value '{value}'")

            for i, (key, value) in keys2.items():  # Add this loop to handle missing keys from keys2
                if (key, value) not in keys1.values():
                    temp_diff = []
                    current_path = f"{path}[{i}]" if path else f"[{i}]"

                    # --- Compare the objects recursively (without hardcoding key names)
                    if not compare_objects(None, obj2[i], current_path, temp_diff, unique_key_candidates):
                        differences.extend(
                            [f"{current_path} (key: {key}, value: {value}): {diff}" for diff in temp_diff])

            return True  # Add this line to explicitly return True if no differences found in the array logic

        else:  # Use stringify approach for other cases (mixed or no keys)
            try:
                keys1 = set(json.dumps(item, sort_keys=True) for item in obj1)
                keys2 = set(json.dumps(item, sort_keys=True) for item in obj2)

                if keys1 != keys2:
                    missing = keys1 - keys2
                    extra = keys2 - keys1
                    if missing:
                        missing_items = [json.loads(item) for item in missing]
                        differences.append(f"Missing array elements at {path}: {missing_items}")
                    if extra:
                        extra_items = [json.loads(item) for item in extra]
                        differences.append(f"Extra array elements at {path}: {extra_items}")
                    return False

            except TypeError:
                differences.append(f"Error comparing array elements at {path}: Could not serialize to JSON.")

            return True

    # Handle primitive values
    else:
        if obj1 != obj2:
            differences.append(f"Value mismatch at {path}: {obj1} vs {obj2}")
            return False
        return True
