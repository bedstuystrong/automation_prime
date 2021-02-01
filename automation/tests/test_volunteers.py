from .helpers import get_random_slack_user_from_volunteer, get_random_volunteer
from ..functions import volunteers


#########
# TESTS #
#########


def test_on_new(mock_slack_client, mock_sendgrid_client):
    test_volunteer = get_random_volunteer()
    test_slack_user = get_random_slack_user_from_volunteer(test_volunteer)

    def mock_users_lookupByEmail(email):
        assert email == test_volunteer.email

        return test_slack_user

    mock_slack_client.return_value.users_lookupByEmail.side_effect = (
        mock_users_lookupByEmail
    )

    volunteers.on_new(test_volunteer)

    assert test_volunteer.slack_handle == test_slack_user.get_handle()
    assert test_volunteer.slack_email == test_slack_user.profile.email
    assert test_volunteer.slack_user_id == test_slack_user.id

    assert mock_sendgrid_client.return_value.send.call_count == 1
