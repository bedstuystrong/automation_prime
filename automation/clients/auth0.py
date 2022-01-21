from pydantic import BaseSettings, SecretStr, constr
import requests
import tenacity

from ..secrets import BaseSecret, SecretsClient
from ..settings import BaseConfig

##########
# CLIENT #
##########


def is_unauthorized(exception):
    return (
        isinstance(exception, requests.exceptions.HTTPError)
        and exception.response.status_code == requests.codes.unauthorized
    )


class Auth0Secrets(BaseSecret):

    _secret_name = "auth0"
    api_token: SecretStr
    client_id: SecretStr
    client_secret: SecretStr


class Auth0Settings(BaseSettings):
    domain: constr(strip_whitespace=True, min_length=1)

    class Config(BaseConfig):
        env_prefix = "auth0_"


class Auth0Client:
    def __init__(self, secrets_client=None, settings=None):
        if secrets_client is None:
            secrets_client = SecretsClient()
        if settings is None:
            settings = Auth0Settings()
        self._base_url = "https://" + settings.domain
        self._api_url = self._base_url + "/api/v2"
        self._secrets_client = secrets_client
        self._secret_obj = None

    @property
    def _secret(self):
        if self._secret_obj is None:
            self._secret_obj = Auth0Secrets.load(self._secrets_client)
        return self._secret_obj

    @property
    def _client_id(self):
        return self._secret.client_id.get_secret_value()

    @property
    def _client_secret(self):
        return self._secret.client_secret.get_secret_value()

    @property
    def _token(self):
        return self._secret.api_token.get_secret_value()

    @_token.setter
    def _token(self, new_token):
        self._secret.api_token._secret_value = new_token
        self._secret.save()

    def _refresh_token(self):
        res = requests.post(
            self._base_url + "/oauth/token",
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "audience": self._api_url + "/",
                "grant_type": "client_credentials",
            },
        )
        res.raise_for_status()
        self._token = res.json()["access_token"]

    @tenacity.retry(
        retry=tenacity.retry_if_exception(is_unauthorized),
        stop=tenacity.stop_after_attempt(1),
    )
    def api_call(self, method, path, json):
        try:
            headers = {
                "Authorization": "Bearer %s" % self._token,
            }
            res = requests.request(
                method, self._api_url + path, headers=headers, json=json
            )
            res.raise_for_status()
            return res.json()
        except requests.exceptions.HTTPError as e:
            if is_unauthorized(e):
                self._refresh_token()
            raise e

    # TODO : support creating users with phone numbers
    def create_user(self, email, name):
        return self.api_call(
            "POST",
            "/users",
            {
                "connection": "email",
                "email": email,
                "name": name,
                "email_verified": True,
            },
        )
