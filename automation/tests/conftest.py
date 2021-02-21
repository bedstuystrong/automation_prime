"""Pytest configuration for tests

Primarily for fixtures and mocks used in multiple test files
"""

import logging
import pytest
from unittest import mock

from ..clients import slack

#########
# SETUP #
#########


# Displays info logs upon test failure
@pytest.fixture(autouse=True)
def _setup_logging(caplog):
    caplog.set_level(logging.INFO)


#########
# MOCKS #
#########


@pytest.fixture
def mock_slack_client():
    with mock.patch(
        f"{slack.__name__}.SlackClient", autospec=True
    ) as mock_client:
        yield mock_client


@pytest.fixture
def mock_sendgrid_client():
    with mock.patch(
        "sendgrid.SendGridAPIClient", autospec=True
    ) as mock_client, mock.patch("sendgrid.helpers.mail.Mail", autospec=True):
        yield mock_client
