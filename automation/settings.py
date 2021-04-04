import os

import pydantic


AUTOMATION_ENV = os.environ.get("AUTOMATION_ENV", "prod")
"""Which .env file to load by default."""


class BaseConfig:
    env_file = f"environments/{AUTOMATION_ENV}.env"


class GoogleCloudSettings(pydantic.BaseSettings):
    project_id: str

    class Config(BaseConfig):
        env_prefix = "google_cloud_"


if __name__ == "__main__":
    from .clients import airtable, auth0, sendgrid, slack

    print("Google Cloud:", GoogleCloudSettings())
    print("Airtable:", airtable.AirtableSettings())
    print("Auth0:", auth0.Auth0Settings())
    print("Sendgrid:", sendgrid.SendgridSettings())
    print("Slack:", slack.SlackSettings())
