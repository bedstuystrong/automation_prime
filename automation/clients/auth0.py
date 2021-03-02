import requests

from automation.config import Auth0Config
from .secrets import SecretsClient

##########
# CLIENT #
##########


class Auth0Client:
    def __init__(self, conf: Auth0Config):
        self._base_url = 'https://%s/api/v2' % conf.domain
        self._token = SecretsClient().get_secret('auth0_api_token')

    def api_call(self, method, path, json):
        # TODO do we need to try/except here or check response status code?
        headers = {
            "Authorization": 'Bearer %s' % self._token,
        }
        resp = requests.request(
            method,
            self._base_url + path,
            headers=headers,
            json=json
        )
        return resp

    def create_user(self, email, name):
        return self.api_call('POST', '/users', {
            "connection": "email",
            "email": email,
            "name": name,
            "email_verified": True,
        })
