import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = PROJECT_ROOT / "code"

# Ensure project root and code directory are in sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))


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