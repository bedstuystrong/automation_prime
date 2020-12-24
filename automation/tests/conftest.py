import logging
import pytest
from unittest import mock

from ..utils import slack, airtable

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
def mock_slack():
    with mock.patch.object(slack, "SlackClient", autospec=True) as mock_client:
        yield mock_client


@pytest.fixture
def mock_airtable_client():
    with mock.patch.object(
        airtable, "AirtableClient", autospec=True
    ) as mock_client:
        yield mock_client
