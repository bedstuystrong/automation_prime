import logging
from slack_logger import SlackHandler, SlackFormatter
from automation import cloud_logging, config, tables  # noqa: E402
#Adding a handler to output error messages from GCP to slack
#Documentation: https://pypi.org/project/slack-logger/
conf = config.load()
sh = SlackHandler(username='gcp_error_bot', icon_emoji=':robot_face:', url=conf.slack.error_bot_webhook)
f = SlackFormatter()
sh.setFormatter(f)
logging.basicConfig(level=logging.INFO, handlers=[sh])
>>>>>>> b345a46 (Adding slack logger)


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
