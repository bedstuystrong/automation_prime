from .. import config
from ..clients import slack

import pytest


@pytest.mark.skip(reason="Hits the slack API")
def test_users_lookupByEmail():
    conf = config.load()
    client = slack.SlackClient(conf.slack)
    test_user_email = conf.slack.test_user_email
    test_user_id = conf.slack.test_user_id

    user = client.users_lookupByEmail(email=test_user_email)
    assert user.id == test_user_id

    user = client.users_lookupByEmail(email="<invalid email>")
    assert user is None
