import os

import pydantic


AUTOMATION_ENV = os.environ.get("AUTOMATION_ENV", "prod")
"""Which .env file to load by default."""


class BaseConfig:
    """For use by pydantic BaseSettings subclasses.

    All of our settings subclasses should use this as the superclass of their
    Config inner classes, to make sure all settings across the project source
    from the same env file (which you can control with AUTOMATION_ENV above).

    A settings class should look like this::

        class FooSettings(pydantic.BaseSettings):
            my_var: str

            class Config(BaseConfig):
                env_prefix = "foo_"

    This way, in .env files or in the process environment, `foo_my_var` will
    control that setting.
    """

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
