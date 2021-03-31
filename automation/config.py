import json
import os
from pathlib import Path
from typing import Dict, Optional

import pydantic

_CHECKOUT_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_CONFIG_PATH = "configs/staging.json"
_CONFIG_ENV_VAR_NAME = "CONFIG"
_ACTIVE_CONFIG_PATH = Path(
    os.environ.get(_CONFIG_ENV_VAR_NAME, _DEFAULT_CONFIG_PATH)
)


class GoogleCloudConfig(pydantic.BaseModel):
    project_id: str


class AirtableConfig(pydantic.BaseModel):
    base_id: str
    api_key: str
    table_names: Dict[str, str]


class Auth0Config(pydantic.BaseModel):
    domain: str
    client_id: str
    client_secret: str


class MailchimpConfig(pydantic.BaseModel):
    api_key: str
    server_prefix: str
    list_id: str


class SlackConfig(pydantic.BaseModel):
    api_key: str
    test_user_email: str
    test_user_id: str
    scim_api_key: str
    resend_invite_webhook: str
    resend_invite_secret: str


class SendgridConfig(pydantic.BaseModel):
    api_key: str
    from_email: str
    from_domain: str
    reply_to: str


class Config(pydantic.BaseModel):
    airtable: AirtableConfig
    auth0: Auth0Config
    mailchimp: MailchimpConfig
    slack: SlackConfig
    sendgrid: SendgridConfig
    google_cloud: Optional[GoogleCloudConfig]


def load():
    config_path = _CHECKOUT_ROOT / _ACTIVE_CONFIG_PATH
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return Config(**json.loads(f.read()))
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Config provided via '{_CONFIG_ENV_VAR_NAME}' does not exist "
            f"(default '{_DEFAULT_CONFIG_PATH}'): {config_path}"
        ) from e
