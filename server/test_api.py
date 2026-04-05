"""Compatibility shim for running the API suite via pytest."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ["DATABASE_PATH"] = str(Path(__file__).resolve().parent / "test_api.db")
os.environ["DEBUG"] = "true"
os.environ["OPENAI_API_KEY"] = ""

API_TEST_PATHS = [
    "server/test_suites/api_nudge_tests.py",
    "server/test_suites/api_action_tests.py",
    "server/test_suites/api_meal_tests.py",
    "server/test_suites/api_signal_tests.py",
    "server/test_suites/api_coach_tests.py",
]


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", *API_TEST_PATHS]))
