"""Compatibility shim for running the engine suite via pytest."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ["OPENAI_API_KEY"] = ""

ENGINE_TEST_PATHS = [
    "server/test_suites/engine_meal_tests.py",
    "server/test_suites/engine_scenario_tests.py",
    "server/test_suites/engine_llm_tests.py",
]


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", *ENGINE_TEST_PATHS]))
