import requests
import tenacity

from automation.config import Auth0Config
from automation.clients import secrets

##########
# CLIENT #
##########

AUTH0_API_TOKEN_SECRET = "auth0_api_token"


def is_unauthorized(exception):
    return (
        isinstance(exception, requests.exceptions.HTTPError)
        and exception.response.status_code == requests.codes.unauthorized
    )


class Auth0Client:
    def __init__(
        self, conf: Auth0Config, secrets_client: secrets.SecretsClient
    ):
        self._base_url = "https://" + conf.domain
        self._api_url = self._base_url + "/api/v2"
        self._client_id = conf.client_id
        self._client_secret = conf.client_secret
        self._secrets_client = secrets_client
        self._token = None

    def _fetch_token(self):
        self._token = self._secrets_client.get_secret(AUTH0_API_TOKEN_SECRET)

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
        token = res.json()["access_token"]
        self._secrets_client.set_secret(AUTH0_API_TOKEN_SECRET, token)
        self._token = token

    @tenacity.retry(
        retry=tenacity.retry_if_exception(is_unauthorized),
        stop=tenacity.stop_after_attempt(1),
    )
    def api_call(self, method, path, json):
        try:
            if self._token is None:
                self._fetch_token()
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
