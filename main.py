import logging

from automation import cloud_logging, tables


cloud_logging.configure()


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################


def poll_members(event, context):
    table = tables.Members()
    success = table.poll_table()
    logging.info("Polling complete" if success else "Polling failed")


def poll_intake(event, context):
    table = tables.Intake()
    success = table.poll_table()
    logging.info("Polling complete" if success else "Polling failed")
