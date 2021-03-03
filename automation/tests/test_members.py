from unittest import mock

from .helpers import (
    TEST_CONFIG,
    get_random_slack_user_from_member,
    get_random_member,
)
from ..clients import auth0
from ..functions import members


#########
# TESTS #
#########


def test_on_new(mock_slack_client, mock_sendgrid_client):
    test_member = get_random_member()
    test_slack_user = get_random_slack_user_from_member(test_member)

    def mock_users_lookupByEmail(email):
        assert email == test_member.email

        return test_slack_user

    mock_auth0_client = mock.Mock(auth0.Auth0Client, autospec=True)

    mock_slack_client.return_value.users_lookupByEmail.side_effect = (
        mock_users_lookupByEmail
    )

    callback = members.NewCallback(TEST_CONFIG)
    callback(test_member)

    assert test_member.slack_handle == test_slack_user.get_handle()
    assert test_member.slack_email == test_slack_user.profile.email
    assert test_member.slack_user_id == test_slack_user.id

    assert mock_sendgrid_client.return_value.send.call_count == 1
    assert mock_auth0_client.return_value.create_user.call_count == 1
