import itertools

import pytest

from ..clients import airtable, auth0, slack
from ..functions import delivery


@pytest.mark.parametrize(
    ["settings_class", "env_file"],
    itertools.product(
        [
            airtable.AirtableSettings,
            auth0.Auth0Settings,
            slack.SlackSettings,
            delivery.DeliverySettings,
        ],
        [
            "environments/dev.env",
            "environments/prod.env",
            "environments/staging.env",
            "environments/test.env",
        ],
    ),
)
def test_load_settings(settings_class, env_file):
    settings_class(_env_file=env_file)
