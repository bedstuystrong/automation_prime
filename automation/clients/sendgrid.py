from pydantic import SecretStr
from sendgrid import SendGridAPIClient

from ..secrets import BaseSecret, SecretsClient


class SendgridSecrets(BaseSecret):

    _secret_name = "sendgrid"
    api_key: SecretStr


# Named like a class so it looks like a constructor, but this doesn't manage
# any of its own state, it just handles getting the api key for you.
def SendgridClient(secrets_client=None):
    if secrets_client is None:
        secrets_client = SecretsClient()
    secrets = SendgridSecrets.load(secrets_client)
    return SendGridAPIClient(secrets.api_key.get_secret_value())
