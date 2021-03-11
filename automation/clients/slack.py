import enum
import random
import string
from typing import Optional

import pydantic
import requests
from six.moves import xrange
import slack_sdk
from slack_sdk import scim
from slack_sdk.scim.v1.user import UserEmail

from automation.config import SlackConfig

##########
# MODELS #
##########


class Channel(pydantic.BaseModel):
    created: int
    creator: str
    id: str
    is_archived: bool
    is_channel: bool
    is_ext_shared: bool
    is_general: bool
    is_group: bool
    is_im: bool
    is_member: bool
    is_mpim: bool
    is_org_shared: bool
    is_pending_ext_shared: bool
    is_private: bool
    is_shared: bool
    name: str
    name_normalized: str
    num_members: int


class Message(pydantic.BaseModel):
    text: str
    ts: float
    user: Optional[str]
    type: str
    subtype: Optional[str]


class Profile(pydantic.BaseModel):
    display_name: Optional[str]
    email: str


class User(pydantic.BaseModel):
    id: str
    is_admin: bool = False
    is_bot: bool = False
    is_owner: bool = False
    name: str
    real_name: Optional[str]
    deleted: bool = False
    profile: Profile

    def get_handle(self):
        # TODO : this logic was copied from the vintage automation, reverify it
        return "@" + (
            self.profile.display_name
            if self.profile.display_name is not None
            else self.real_name
        )


##########
# CLIENT #
##########

_USERS_NOT_FOUND = "users_not_found"


class SlackErrors(enum.Enum):
    USERS_NOT_FOUND = "users_not_found"


def generate_password(length):
    charset = string.ascii_letters + string.digits
    return "".join(
        [random.SystemRandom().choice(charset) for _ in xrange(length)]
    )


# TODO : add support for other slack client methods
#
# TODO : make the interface better and support pagination and
# retrying (upon rate limiting):
#
# Example Interface:
#    slack = SlackClient()
#    user = slack.users.find(email='leif@example.com')
class SlackClient:
    def __init__(self, conf: SlackConfig):
        self._slack_sdk_client = slack_sdk.WebClient(token=conf.api_key)
        self._slack_scim_client = scim.SCIMClient(token=conf.scim_api_key)
        self._resend_invite_webhook = conf.resend_invite_webhook
        self._resend_invite_secret = conf.resend_invite_secret

    def _slack_sdk_wrapper(
        self, slack_sdk_func_name, model_type, data_key, single_result=False
    ):
        def wrapper(*args, **kwargs):
            slack_sdk_func = getattr(
                self._slack_sdk_client, slack_sdk_func_name
            )

            res = slack_sdk_func(*args, **kwargs)

            if single_result:
                return model_type(**res.data[data_key])
            else:
                return [model_type(**e) for e in res.data[data_key]]

        return wrapper

    def _create_scim_user(self, email, name):
        user = scim.User(
            user_name=name,
            display_name=name,
            active=True,
            password=generate_password(32),
            emails=[UserEmail(value=email, primary=True)],
        )
        create_result = self._slack_scim_client.create_user(user)
        return create_result.user

    def _resend_invite(self, email):
        headers = {
            "Authorization": "Bearer %s" % self._resend_invite_secret,
        }
        res = requests.post(
            self._resend_invite_webhook, headers=headers, json={"email": email}
        )
        res.raise_for_status()
        return res.text

    def users_lookupByEmail(self, email):
        try:
            return self._slack_sdk_wrapper(
                "users_lookupByEmail",
                User,
                "user",
                single_result=True,
            )(email=email)
        except slack_sdk.errors.SlackApiError as e:
            if e.response.data["error"] == SlackErrors.USERS_NOT_FOUND.value:
                return None
            else:
                raise

    def users_invite(self, email, name):
        user = self._create_scim_user(email, name)
        self._resend_invite(email)
        return User(
            id=user.id,
            name=name,
            profile=Profile(
                email=email,
            ),
        )
