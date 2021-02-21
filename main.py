import logging

logging.basicConfig(level=logging.INFO)

from automation import config, tables  # noqa: E402


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################


def poll_members(event, context):
    conf = config.load()
    client = tables.MEMBERS.get_airtable_client(conf.airtable)
    success = client.poll_table(conf)
    logging.info("Polling complete" if success else "Polling failed")
