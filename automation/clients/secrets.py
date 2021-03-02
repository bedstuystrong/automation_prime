from google.cloud import secretmanager

from .. import config

##########
# CLIENT #
##########


class SecretsClient:
    def __init__(self):
        self._client = secretmanager.SecretManagerServiceClient()
        self._project_id = config.load().google_cloud.project_id

    def get_secret(self, name):
        secret_name = 'projects/%s/secrets/%s/versions/latest' % (
            self._project_id,
            name
        )
        response = self._client.access_secret_version({
            "name": secret_name
        })
        return response.payload.data.decode("UTF-8")
