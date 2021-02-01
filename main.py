import logging

logging.basicConfig(level=logging.INFO)

from automation import tables  # noqa: E402
from automation.utils import airtable  # noqa: E402


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################


def poll_members(event, context):
    airtable.poll_table(
        airtable.AirtableClient(), tables.Table.VOLUNTEERS.value
    )
