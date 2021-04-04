import enum
import random
import string
from typing import Optional

import pydantic
import requests
import slack_sdk
from slack_sdk import scim
from slack_sdk.scim.v1.user import UserEmail
import structlog

from ..secrets import BaseSecret, SecretsClient
from ..settings import BaseConfig

log = structlog.get_logger("slack_api")


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


class SlackSecrets(BaseSecret):

    _secret_name = "slack"
    api_key: pydantic.SecretStr
    scim_api_key: pydantic.SecretStr
    resend_invite_secret: pydantic.SecretStr


class SlackSettings(pydantic.BaseSettings):
    test_user_email: Optional[str]
    test_user_id: Optional[str]
    resend_invite_webhook: str

    class Config(BaseConfig):
        env_prefix = "slack_"


class SlackErrors(enum.Enum):
    USERS_NOT_FOUND = "users_not_found"


def generate_password(length):
    charset = string.ascii_letters + string.digits
    return "".join(
        [random.SystemRandom().choice(charset) for _ in range(length)]
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
    def __init__(
        self, secrets_client=SecretsClient(), settings=SlackSettings()
    ):
        secrets = SlackSecrets.load(secrets_client)
        self._slack_sdk_client = slack_sdk.WebClient(
            token=secrets.api_key.get_secret_value()
        )
        self._slack_scim_client = scim.SCIMClient(
            token=secrets.scim_api_key.get_secret_value()
        )
        self._resend_invite_webhook = settings.resend_invite_webhook
        self._resend_invite_secret = (
            secrets.resend_invite_secret.get_secret_value()
        )

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
        if create_result.status_code == 201:
            return create_result.user
        else:
            log.error(create_result.errors.description, email=email)
            return None

    def _resend_invite(self, email):
        try:
            headers = {
                "Authorization": "Bearer %s" % self._resend_invite_secret,
            }
            res = requests.post(
                self._resend_invite_webhook,
                headers=headers,
                json={"email": email},
            )
            res.raise_for_status()
            return res.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == requests.codes.not_found:
                log.warning("Failed to send invite", email=email)
                return None
            else:
                raise

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
        if user:
            self._resend_invite(email)
            return User(
                id=user.id,
                name=name,
                profile=Profile(
                    email=email,
                ),
            )
