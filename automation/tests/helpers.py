from datetime import datetime, timedelta
import random
import string

from .. import config
from ..models import MemberModel
from ..clients import slack


TEST_CONFIG = config.Config(
    **{
        "airtable": {
            "base_id": "",
            "api_key": "",
            "table_names": {
                "inbound": "",
                "volunteer": "",
                "foo": "some table name",
            },
        },
        "slack": {
            "api_key": "",
            "test_user_email": "",
            "test_user_id": "",
            "scim_api_key": "",
            "resend_invite_webhook": "",
            "resend_invite_secret": "",
        },
        "sendgrid": {
            "api_key": "",
            "from_email": "",
            "from_domain": "",
            "reply_to": "",
        },
        "auth0": {
            "domain": "",
            "client_id": "",
            "client_secret": "",
        },
        "mailchimp": {"api_key": "", "server_prefix": "", "list_id": ""},
        "google_cloud": {"project_id": ""},
    }
)


def get_random_string(length=16):
    return "".join(random.choices(list(string.ascii_lowercase), k=length))


def get_random_created_at():
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)

    random_timestamp = random.uniform(
        one_year_ago.timestamp(), now.timestamp()
    )

    return datetime.fromtimestamp(random_timestamp)


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
            "Preferred Method of Communication": ["Email"],
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
