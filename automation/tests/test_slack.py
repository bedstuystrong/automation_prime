from .. import config
from ..utils import slack

import pytest


@pytest.fixture
def test_config():
    return config.Config.load()


@pytest.fixture
def test_user_email(test_config):
    return test_config.slack.test_user_email


@pytest.fixture
def test_user_id(test_config):
    return test_config.slack.test_user_id


@pytest.mark.skip(reason="Hits the slack API")
def test_users_lookupByEmail(test_user_email, test_user_id):
    client = slack.SlackClient()

    user = client.users_lookupByEmail(email=test_user_email)
    assert user.id == test_user_id

    user = client.users_lookupByEmail(email="<invalid email>")
    assert user is None
