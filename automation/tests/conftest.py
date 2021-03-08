"""Pytest configuration for tests

Primarily for fixtures used in multiple test files
"""

import logging

import pytest

#########
# SETUP #
#########


# Displays info logs upon test failure
@pytest.fixture(autouse=True)
def _setup_logging(caplog):
    caplog.set_level(logging.INFO)
