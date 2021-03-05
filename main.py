import logging

from automation import cloud_logging, config, tables  # noqa: E402


cloud_logging.configure()
conf = config.load()


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################


def poll_members(event, context):
    table = tables.Members(conf)
    success = table.poll_table()
    logging.info("Polling complete" if success else "Polling failed")


def poll_intake(event, context):
    table = tables.Intake(conf)
    success = table.poll_table()
    logging.info("Polling complete" if success else "Polling failed")
