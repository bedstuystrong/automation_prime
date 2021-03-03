from google.cloud import secretmanager

from automation.config import GoogleCloudConfig

##########
# CLIENT #
##########


class SecretsClient:
    def __init__(self, conf: GoogleCloudConfig):
        self._client = secretmanager.SecretManagerServiceClient()
        self._project_id = conf.project_id

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
