import json

import pytest

from .helpers import TEST_ENV, MockSecretsClient
from ..clients import slack


TEST_SECRETS_CLIENT = MockSecretsClient(
    slack=json.dumps(
        {"api_key": "", "scim_api_key": "", "resend_invite_secret": ""}
    )
)
TEST_SETTINGS = slack.SlackSettings(_env_file=TEST_ENV)


@pytest.mark.skip(reason="Hits the slack API")
def test_users_lookupByEmail():
    client = slack.SlackClient(settings=TEST_SETTINGS)
    test_user_email = TEST_SETTINGS.test_user_email
    test_user_id = TEST_SETTINGS.test_user_id

    user = client.users_lookupByEmail(email=test_user_email)
    assert user.id == test_user_id

    user = client.users_lookupByEmail(email="<invalid email>")
    assert user is None
