import random
import string

from ..models import VolunteerModel
from ..utils import slack


def get_random_string(length=16):
    return "".join(random.choices(list(string.ascii_lowercase), k=length))


def get_random_airtable_id():
    return get_random_string()


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
