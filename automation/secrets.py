from typing import ClassVar, Text

from google.cloud import secretmanager
from pydantic import BaseModel, SecretBytes, SecretStr

from .settings import GoogleCloudSettings


class SecretsClient:
    def __init__(self, settings=GoogleCloudSettings()):
        self._client = secretmanager.SecretManagerServiceClient()
        self._project_id = settings.project_id

    def set_secret(self, name, value):
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
        latest_secret_path = self._client.secret_version_path(
            self._project_id, name, "latest"
        )
        res = self._client.access_secret_version({"name": latest_secret_path})
        return res.payload.data.decode("UTF-8")


class BaseSecret(BaseModel):

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
        """JSON encoder to write secrets in plaintext."""
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
    from .clients import airtable, auth0, slack

    print("Airtable:", airtable.AirtableSecrets.load())
    print("Auth0:", auth0.Auth0Secrets.load())
    print("Slack:", slack.SlackSecrets.load())
    print("Sendgrid:", SendgridSecrets.load())
