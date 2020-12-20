from .. import config
from ..utils import slack

import pytest

TEST_USER_EMAIL = config.Config.load().slack.test_user_email
TEST_USER_ID = config.Config.load().slack.test_user_id


@pytest.mark.skip(reason="Hits the slack API")
def test_users_lookupByEmail():
    client = slack.SlackClient()

    user = client.users_lookupByEmail(email=TEST_USER_EMAIL)
    assert user.id == TEST_USER_ID

    user = client.users_lookupByEmail(email="<invalid email>")
    assert user is None
