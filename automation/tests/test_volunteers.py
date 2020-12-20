import random
import string
from unittest.mock import patch

import pytest

from ..functions import volunteers
from ..models import VolunteerModel
from ..utils import slack

#########
# UTILS #
#########


def get_random_string(length=16):
    return "".join(random.choices(list(string.ascii_lowercase), k=length))


def get_random_volunteer():
    return VolunteerModel(
        id=get_random_string(),
        **{
            "Name": get_random_string() + " " + get_random_string(),
            "Phone Number": get_random_string(),
            "Email Address": get_random_string(),
        }
    )


def get_random_slack_user_from_volunteer(volunteer):
    return slack.User(
        id=get_random_string(),
        name=get_random_string(),
        profile=slack.Profile(
            email=volunteer.email,
            display_name=get_random_string(),
        ),
    )


#########
# MOCKS #
#########


@pytest.fixture
def mock_slack():
    with patch.object(slack, "SlackClient", autospec=True) as mock_client:
        yield mock_client


#########
# TESTS #
#########


def test_on_new(mock_slack):
    test_volunteer = get_random_volunteer()
    test_slack_user = get_random_slack_user_from_volunteer(test_volunteer)

    def mock_users_lookupByEmail(email):
        assert email == test_volunteer.email

        return test_slack_user

    mock_slack.return_value.users_lookupByEmail.side_effect = (
        mock_users_lookupByEmail
    )

    volunteers.on_new(test_volunteer)

    assert test_volunteer.slack_handle == test_slack_user.get_handle()
    assert test_volunteer.slack_email == test_slack_user.profile.email
    assert test_volunteer.slack_user_id == test_slack_user.id
