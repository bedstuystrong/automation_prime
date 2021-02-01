import logging

import sendgrid

from .. import config
from ..utils import slack, templates

logger = logging.getLogger(__name__)


def on_new(volunteer_model):
    # TODO : the volunteer may not have joined slack yet, so we should
    # try and update their slack info again later

    # Lookup and store the volunteer's slack metadata
    slack_client = slack.SlackClient()
    slack_user = slack_client.users_lookupByEmail(volunteer_model.email)

    if slack_user is not None:
        volunteer_model.slack_handle = slack_user.get_handle()
        volunteer_model.slack_email = slack_user.profile.email
        volunteer_model.slack_user_id = slack_user.id
    else:
        logger.warning(
            "Couldn't find slack user for: {}".format(volunteer_model.email)
        )

    # Send the new member email
    sendgrid_client = sendgrid.SendGridAPIClient(
        config.Config.load().sendgrid.api_key
    )
    sendgrid_client.send(
        sendgrid.helpers.mail.Mail(
            from_email=config.Config.load().sendgrid.from_email,
            to_emails=volunteer_model.email,
            subject="Welcome to Bed-Stuy Strong {}!".format(
                volunteer_model.name
            ),
            html_content=templates.render("new_member_email.html.jinja"),
        )
    )

    volunteer_model.status = "Processed"
