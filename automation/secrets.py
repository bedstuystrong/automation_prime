from typing import ClassVar, Text

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import secretmanager
from pydantic import BaseModel, SecretBytes, SecretStr
import structlog

from .settings import GoogleCloudSettings


logger = structlog.get_logger(__name__)


class InvalidCredentialsError(Exception):
    """No valid credentials for Secret Manager API available."""


class SecretsClient:
    def __init__(self, settings=GoogleCloudSettings()):
        # If we don't have credentials, construct a non-working SecretsClient,
        # we'll fail later if something tries to fetch secrets, but that
        # doesn't happen during unit tests.
        try:
            self._client = secretmanager.SecretManagerServiceClient()
        except DefaultCredentialsError:
            logger.warning(
                "Could not connect to Secret manager with default "
                "credentials. Secrets will be unavailable."
            )
            self._client = None
        self._project_id = settings.project_id

    def set_secret(self, name, value):
        if self._client is None:
            raise InvalidCredentialsError()
        secret_path = self._client.secret_path(self._project_id, name)
        self._client.add_secret_version(
            {
                "parent": secret_path,
                "payload": {
                    "data": value.encode("UTF-8"),
                },
            }
        )
        return self.get_secret(name)

    def get_secret(self, name):
        if self._client is None:
            raise InvalidCredentialsError()
        latest_secret_path = self._client.secret_version_path(
            self._project_id, name, "latest"
        )
        res = self._client.access_secret_version({"name": latest_secret_path})
        return res.payload.data.decode("UTF-8")


class BaseSecret(BaseModel):
    """Helper base class for loading secrets and validating with pydantic.

    Subclasses must define _secret_name (to be unique for the Google Cloud
    Project), and secrets are expected to contain JSON defining each pydantic
    field in the class.
    """

    _secret_name: ClassVar[Text]
    _secrets_client: SecretsClient

    class Config:
        underscore_attrs_are_private = True

    @classmethod
    def load(cls, secrets_client=SecretsClient()):
        """Load a secret from Secret Manager."""
        data = secrets_client.get_secret(cls._secret_name)
        secrets = cls.parse_raw(data)
        secrets._secrets_client = secrets_client
        return secrets

    @staticmethod
    def _plaintext_encode(value):
        """JSON encoder to write secrets in plaintext.

        It's possible to set some Config options that will make .json()
        serialize all secret values in plaintext, but we do it this way so that
        only in save() do we serialize plaintext values. This way, if someone
        accidentally logs secret.json() somewhere, the secret values will be
        sanitized in logs.
        """
        if isinstance(value, (SecretStr, SecretBytes)):
            return value.get_secret_value()
        return value

    def save(self):
        """Save the current secret back to Secret Manager."""
        payload = self.json(encoder=self._plaintext_encode)
        self._secrets_client.set_secret(self._secret_name, payload)


class SendgridSecrets(BaseSecret):

    _secret_name = "sendgrid"
    api_key: SecretStr


if __name__ == "__main__":
    from .clients import airtable, auth0, mailchimp, slack

    print("Airtable:", airtable.AirtableSecrets.load())
    print("Auth0:", auth0.Auth0Secrets.load())
    print("Mailchimp:", mailchimp.MailchimpSecrets.load())
    print("Slack:", slack.SlackSecrets.load())
    print("Sendgrid:", SendgridSecrets.load())
