import logging
from slack_logger import SlackHandler, SlackFormatter

#Adding a handler to output error messages from GCP to slack
#Documentation: https://pypi.org/project/slack-logger/
sh = SlackHandler(username='gcp_error_bot', icon_emoji=':robot_face:', url='https://hooks.slack.com/services/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')
f = SlackFormatter()
sh.setFormatter(f)
logging.basicConfig(level=logging.INFO, handlers=[sh])

from automation import config, tables  # noqa: E402


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################


def poll_members(event, context):
    conf = config.load()
    client = tables.MEMBERS.get_airtable_client(conf.airtable)
    success = client.poll_table(conf)
    logging.info("Polling complete" if success else "Polling failed")
