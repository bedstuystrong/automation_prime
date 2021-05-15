import hashlib
import mailchimp_marketing as MailchimpMarketing

from pydantic import BaseSettings, SecretStr, constr

from ..secrets import BaseSecret, SecretsClient
from ..settings import BaseConfig


class MailchimpSecrets(BaseSecret):
    _secret_name = "mailchimp"
    api_key: SecretStr


class MailchimpSettings(BaseSettings):
    list_id: constr(strip_whitespace=True, min_length=1)
    server_prefix: constr(strip_whitespace=True, min_length=1)

    class Config(BaseConfig):
        env_prefix = "mailchimp_"


##########
# CLIENT #
##########


class MailchimpClient:
    def __init__(self, secrets_client=None, settings=None):
        if secrets_client is None:
            secrets_client = SecretsClient()
        if settings is None:
            settings = MailchimpSettings()
        secrets = MailchimpSecrets.load(secrets_client)
        self._client = MailchimpMarketing.Client()
        self._client.set_config(
            {
                "api_key": secrets.api_key.get_secret_value(),
                "server": settings.server_prefix,
            }
        )
        self._list_id = settings.list_id

    def _hash(self, email):
        string = email.lower().encode(encoding="utf-8")
        return hashlib.md5(string).hexdigest()

    def subscribe(self, email):
        member_info = {
            "email_address": email,
            "status": "subscribed",
            "status_if_new": "subscribed",
        }

        return self._client.lists.set_list_member(
            self._list_id, self._hash(email), member_info
        )
