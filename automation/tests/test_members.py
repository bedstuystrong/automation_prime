from unittest import mock

import sendgrid

from .helpers import (
    get_random_slack_user_from_member,
    get_random_member,
    TEST_CONFIG,
)
from ..clients import slack, auth0
from ..functions import members


#########
# TESTS #
#########


def test_on_new():
    test_member = get_random_member()
    test_slack_user = get_random_slack_user_from_member(test_member)

    def mock_users_lookup_by_email(email):
        assert email == test_member.email

        return test_slack_user

    def mock_create_user(email, name):
        assert email == test_member.email
        assert name == test_member.name

    mock_auth0_client = mock.Mock(auth0.Auth0Client, autospec=True)
    mock_auth0_client.create_user.side_effect = mock_create_user

    # NOTE that we have to use an instance of `SlackClient` to mock, because
    # we set properties in the constructor that autospec can't detect when
    # creating a mock from the class
    mock_slack_client = mock.Mock(
        slack.SlackClient(TEST_CONFIG.slack), autospec=True
    )
    mock_slack_client.users.lookup_by_email.side_effect = (
        mock_users_lookup_by_email
    )
    mock_sendgrid_client = mock.Mock(sendgrid.SendGridAPIClient, autospec=True)

    members.on_new(
        test_member,
        slack_client=mock_slack_client,
        sendgrid_client=mock_sendgrid_client,
        auth0_client=mock_auth0_client,
        from_email="test@example.org",
    )

    assert test_member.slack_email == test_slack_user.profile.email
    assert test_member.slack_user_id == test_slack_user.id

    assert mock_sendgrid_client.send.call_count == 1
    assert mock_auth0_client.create_user.call_count == 1

    def mock_users_lookup_by_email_none(email):
        return None

    def mock_users_invite(email, name):
        assert email == test_member.email
        assert name == test_member.name

        return test_slack_user

    mock_slack_client.users.lookup_by_email.side_effect = (
        mock_users_lookup_by_email_none
    )
    mock_slack_client.users.invite.side_effect = mock_users_invite

    members.on_new(
        test_member,
        slack_client=mock_slack_client,
        sendgrid_client=mock_sendgrid_client,
        auth0_client=mock_auth0_client,
        from_email="test@example.org",
    )

    assert mock_slack_client.users.invite.call_count == 1
