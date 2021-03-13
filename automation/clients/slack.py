import datetime
import enum
import secrets
import string
import time
from typing import Optional

import pydantic
import requests
import slack_sdk
import structlog
from slack_sdk import scim
from slack_sdk.scim.v1.user import UserEmail

from automation.config import SlackConfig

log = structlog.get_logger("slack_api")

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


class TeamLog(pydantic.BaseModel):
    user_id: str
    username: str
    date_first: datetime.datetime
    date_last: datetime.datetime
    count: int
    country: Optional[str]
    region: Optional[str]
    user_agent: str
    isp: Optional[str]

    @pydantic.validator("country", "region", "isp", pre=True)
    def validate_maybe_empty_str(cls, v):
        if v == "":
            return None

        return v


#########
# UTILS #
#########


def _generate_password(length=32):
    charset = string.ascii_letters + string.digits
    return "".join(secrets.choice(charset) for _ in range(length))


##########
# CLIENT #
##########


class SlackErrorCodes(enum.Enum):
    USERS_NOT_FOUND = "users_not_found"
    OVER_PAGINATION_LIMIT = "over_pagination_limit"
    RATE_LIMITED = "ratelimited"


class SlackMethodType(enum.Enum):
    # Method returns only one result
    SINGLE_RESULT = 0
    # Method returns a list of results
    MULTIPLE_RESULTS = 1
    # Method returns a list of results, acrros multiple pages
    # NOTE that result must include "paging" entry
    MULTIPLE_RESULTS_PAGINATED = 1


def _slack_sdk_wrapper(
    slack_sdk_client_func,
    model_type,
    data_key,
    method_type,
    num_results_per_page=None,
):
    """A wrapper for slack sdk client functions

    Provides some abstractions for interacting with the Slack API via a Slack
    SDK client function, including:
        - Support for multiple types of Slack API methods
            + Single result
            + Multiple result
            + Multiple result (paginated)
        - Retrying on rate limiting
        - Parsing results into provided model

    Args:
        slack_sdk_client_func: The Slack client function to call
        model_type: The pydantic model class to use to parse results
        data_key: The key for the Slack response (e.g. "user")
        method_type: An enum corresponding to the method protocol
    """
    RATE_LIMIT_SLEEP_SEC = 1.5

    if (
        num_results_per_page is not None
        and method_type != SlackMethodType.MULTIPLE_RESULTS_PAGINATED
    ):
        raise ValueError(
            "Items per page can only be specified when paginating"
        )

    def _rate_limit_wrapper(func):
        """Handles retrying when rate limited"""

        def wrapper(*args, **kwargs):
            while True:
                try:
                    return func(*args, **kwargs)
                except slack_sdk.errors.SlackApiError as e:
                    if (
                        e.response.data["error"]
                        == SlackErrorCodes.RATE_LIMITED.value
                    ):
                        # TODO : add some logging if we get rate limited
                        time.sleep(RATE_LIMIT_SLEEP_SEC)
                    else:
                        raise

        return wrapper

    def _wrap_single_result(*args, **kwargs):
        res = _rate_limit_wrapper(slack_sdk_client_func)(*args, **kwargs)
        return model_type(**res.data[data_key])

    def _wrap_multiple_results(*args, **kwargs):
        res = _rate_limit_wrapper(slack_sdk_client_func)(*args, **kwargs)

        return (model_type(**e) for e in res.data[data_key])

    def _wrap_multiple_results_paginated(*args, **kwargs):
        cur_page: Optional[int] = None

        while True:
            try:
                res = _rate_limit_wrapper(slack_sdk_client_func)(
                    *args, **kwargs, page=cur_page, count=num_results_per_page
                )
            except slack_sdk.errors.SlackApiError as e:
                if (
                    e.response.data["error"]
                    == SlackErrorCodes.OVER_PAGINATION_LIMIT.value
                ):
                    break
                else:
                    raise

            assert cur_page == res["paging"]["page"] or (
                cur_page is None and res["paging"]["page"] == 1
            )

            for e in res.data[data_key]:
                yield model_type(**e)

            if cur_page == res["paging"]["pages"]:
                break

            cur_page = res["paging"]["page"] + 1

    if method_type == SlackMethodType.SINGLE_RESULT:
        return _wrap_single_result
    elif method_type == SlackMethodType.MULTIPLE_RESULTS:
        return _wrap_multiple_results
    elif method_type == SlackMethodType.MULTIPLE_RESULTS_PAGINATED:
        return _wrap_multiple_results_paginated
    else:
        raise ValueError(
            f"No wrapper for provided method type: {method_type.name}"
        )


class SlackClient:
    """A wrapper client for the Slack API

    This client provides an interface for interacting with the Slack API,
    abstracting away much of the nonsense. Functionality is categorized into
    namespaces (e.g. `client.users.info` and `client.team.access_logs`).
    All results are serialized into pydantic models. And methods return
    iterators.

    Example:
        client = SlackClient(conf.slack)
        slack_user = client.users.info(<slack id>)
        assert slack_user.name == "blah"
    """

    class Team:
        def __init__(self, slack_client):
            self._slack_client = slack_client

        def access_logs(self, after=None) -> TeamLog:
            """Get access logs after the provided date

            NOTE that we provide a different interface than the Slack method,
            which uses "before" instead of "after"

            NOTE this function can take a long time to run in large workspaces
            when fetching more than a few days worth of results
            """
            if self._slack_client._user_slack_sdk_client is None:
                raise RuntimeError(
                    "Cannot access admin API without a user Slack token"
                )

            # The last result returned from the API
            last_result = None
            # The last "before" date we requested, none in the first call
            last_before = None

            while True:
                before = (
                    int(last_result.date_last.timestamp())
                    if last_result is not None
                    else None
                )

                if last_before is not None:
                    assert before is not None
                    assert before < last_before, (
                        "Requested before date must always older than last "
                        "before"
                    )

                last_before = before

                results = _slack_sdk_wrapper(
                    self._slack_client._user_slack_sdk_client.team_accessLogs,
                    TeamLog,
                    "logins",
                    SlackMethodType.MULTIPLE_RESULTS_PAGINATED,
                    # NOTE that this is the maximum
                    num_results_per_page=1000,
                )(
                    before=before,
                )

                # WARNING the results are not always in order, that is the
                # date first and date last is very rarely greater than the
                # previous result
                num_results = 0
                for res in results:
                    # NOTE that sometimes the slack API returns duplicates :(
                    #
                    # TODO we might still be returning duplicates on page
                    # boundaries or when setting `before` to bypass the
                    # maximum pagination limits
                    if res == last_result:
                        continue

                    # Check to see if we've reached our `after` date
                    if after is not None and res.date_first < after:
                        return

                    num_results += 1
                    last_result = res
                    yield res

                # If there are no more results, return.
                if num_results == 0:
                    return

                # If "after" wasn't provided, we've returned results from all
                # pages, return.
                if after is None:
                    return

    class Users:
        def __init__(self, slack_client):
            self._slack_client = slack_client

        def _create_scim_user(self, email, name) -> scim.User:
            user = scim.User(
                user_name=name,
                display_name=name,
                active=True,
                password=_generate_password(32),
                emails=[UserEmail(value=email, primary=True)],
            )
            create_result = self._slack_client._slack_scim_client.create_user(
                user
            )
            if create_result.status_code == 201:
                return create_result.user
            else:
                log.error(create_result.errors.description, email=email)
                return None

        def _resend_invite(self, email) -> None:
            try:
                headers = {
                    "Authorization": f"Bearer {self._slack_client._resend_invite_secret}",
                }
                res = requests.post(
                    self._slack_client._resend_invite_webhook,
                    headers=headers,
                    json={"email": email},
                )
                res.raise_for_status()
                return
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == requests.codes.not_found:
                    log.warning("Failed to send invite", email=email)
                    return
                else:
                    raise

        def info(self, slack_id) -> Optional[User]:
            try:
                return _slack_sdk_wrapper(
                    self._slack_client._bot_user_slack_sdk_client.users_info,
                    User,
                    "user",
                    SlackMethodType.SINGLE_RESULT,
                )(user=slack_id)
            except slack_sdk.errors.SlackApiError as e:
                if (
                    e.response.data["error"]
                    == SlackErrorCodes.USERS_NOT_FOUND.value
                ):
                    return None
                else:
                    raise

        def lookup_by_email(self, email) -> Optional[User]:
            try:
                client = self._slack_client._bot_user_slack_sdk_client
                return _slack_sdk_wrapper(
                    client.users_lookupByEmail,
                    User,
                    "user",
                    SlackMethodType.SINGLE_RESULT,
                )(email=email)
            except slack_sdk.errors.SlackApiError as e:
                if (
                    e.response.data["error"]
                    == SlackErrorCodes.USERS_NOT_FOUND.value
                ):
                    return None
                else:
                    raise

        def invite(self, email, name) -> Optional[User]:
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

    def __init__(self, conf: SlackConfig):
        self._bot_user_slack_sdk_client = slack_sdk.WebClient(
            token=conf.bot_user_token
        )
        # NOTE that the user token is only used for methods requiring admin
        # functionality
        self._user_slack_sdk_client = (
            slack_sdk.WebClient(token=conf.user_token)
            if conf.user_token is not None
            else None
        )
        self._slack_scim_client = scim.SCIMClient(token=conf.scim_api_key)
        self._resend_invite_webhook = conf.resend_invite_webhook
        self._resend_invite_secret = conf.resend_invite_secret

        self.team = SlackClient.Team(self)
        self.users = SlackClient.Users(self)
