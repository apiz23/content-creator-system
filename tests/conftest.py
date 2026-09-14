import pytest


def pytest_ignore_collect(collection_path):
    """Don't collect plugin source files as test modules."""
    path_str = str(collection_path)
    if path_str.endswith("__init__.py"):
        return True
    if path_str.endswith("schemas.py"):
        return True
    if path_str.endswith("tools.py"):
        return True
    return False
