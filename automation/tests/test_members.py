from unittest import mock

import sendgrid

from .helpers import (
    get_random_slack_user_from_member,
    get_random_member,
)
from ..clients import slack, auth0
from ..functions import members


#########
# TESTS #
#########


def test_on_new():
    test_member = get_random_member()
    test_slack_user = get_random_slack_user_from_member(test_member)

    def mock_users_lookupByEmail(email):
        assert email == test_member.email

        return test_slack_user

    def mock_create_user(email, name):
        assert email == test_member.email
        assert name == test_member.name

    mock_auth0_client = mock.Mock(auth0.Auth0Client, autospec=True)
    mock_auth0_client.create_user.side_effect = mock_create_user

    mock_slack_client = mock.Mock(slack.SlackClient, autospec=True)
    mock_slack_client.users_lookupByEmail.side_effect = (
        mock_users_lookupByEmail
    )
    mock_sendgrid_client = mock.Mock(sendgrid.SendGridAPIClient, autospec=True)

    members.on_new(
        test_member,
        slack_client=mock_slack_client,
        sendgrid_client=mock_sendgrid_client,
        auth0_client=mock_auth0_client,
        from_email="test@example.org",
    )

    assert test_member.slack_user_id == test_slack_user.id

    assert mock_sendgrid_client.send.call_count == 1
    assert mock_auth0_client.create_user.call_count == 1

    def mock_users_lookupByEmail_none(email):
        return None

    def mock_users_invite(email, name):
        assert email == test_member.email
        assert name == test_member.name

        return test_slack_user

    mock_slack_client.users_lookupByEmail.side_effect = (
        mock_users_lookupByEmail_none
    )
    mock_slack_client.users_invite.side_effect = mock_users_invite

    members.on_new(
        test_member,
        slack_client=mock_slack_client,
        sendgrid_client=mock_sendgrid_client,
        auth0_client=mock_auth0_client,
        from_email="test@example.org",
    )

    assert mock_slack_client.users_invite.call_count == 1
