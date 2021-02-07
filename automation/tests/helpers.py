from datetime import timedelta
import random
import string

from ..models import MemberModel
from ..utils import slack


def get_random_string(length=16):
    return "".join(random.choices(list(string.ascii_lowercase), k=length))


def get_random_created_at():
    import datetime

    now = datetime.datetime.now()
    one_year_ago = now - datetime.timedelta(days=365)

    random_timestamp = random.uniform(one_year_ago.timestamp(), now.timestamp())

    return datetime.datetime.fromtimestamp(random_timestamp)


def get_random_airtable_id():
    return get_random_string()


def get_random_member():
    return MemberModel(
        id=get_random_string(),
        created_at=get_random_created_at(),
        **{
            "Name": get_random_string() + " " + get_random_string(),
            "Phone Number": get_random_string(),
            "Email Address": get_random_string(),
        }
    )


def get_random_slack_user_from_member(member):
    return slack.User(
        id=get_random_string(),
        name=get_random_string(),
        profile=slack.Profile(
            email=member.email,
            display_name=get_random_string(),
        ),
    )
