import logging

import sendgrid

from .. import config
from ..utils import slack, templates

logger = logging.getLogger(__name__)


def on_new(member_model):
    # TODO : the member may not have joined slack yet, so we should
    # try and update their slack info again later

    # Lookup and store the member's slack metadata
    slack_client = slack.SlackClient()
    slack_user = slack_client.users_lookupByEmail(member_model.email)

    if slack_user is not None:
        member_model.slack_handle = slack_user.get_handle()
        member_model.slack_email = slack_user.profile.email
        member_model.slack_user_id = slack_user.id
    else:
        logger.warning(
            "Couldn't find slack user for: {}".format(member_model.email)
        )

    # Send the new member email
    sendgrid_client = sendgrid.SendGridAPIClient(
        config.Config.load().sendgrid.api_key
    )
    sendgrid_client.send(
        sendgrid.helpers.mail.Mail(
            from_email=config.Config.load().sendgrid.from_email,
            to_emails=member_model.email,
            subject="Welcome to Bed-Stuy Strong {}!".format(
                member_model.name
            ),
            html_content=templates.render("new_member_email.html.jinja"),
        )
    )

    member_model.status = "Processed"
