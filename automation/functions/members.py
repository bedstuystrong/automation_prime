import logging

import sendgrid

from .. import config
from ..clients import auth0, slack, templates

logger = logging.getLogger(__name__)


class NewCallback:
    def __init__(self, conf: config.Config):
        self.slack_client = slack.SlackClient(conf.slack)
        self.sendgrid_client = sendgrid.SendGridAPIClient(
            conf.sendgrid.api_key
        )
        self.auth0_client = auth0.Auth0Client(conf.auth0, conf.google_cloud)
        self.from_email = conf.sendgrid.from_email

    def __call__(self, member_model):
        # TODO : the member may not have joined slack yet, so we should
        # try and update their slack info again later

        # Lookup and store the member's slack metadata
        slack_user = self.slack_client.users_lookupByEmail(member_model.email)

        if slack_user is not None:
            member_model.slack_handle = slack_user.get_handle()
            member_model.slack_email = slack_user.profile.email
            member_model.slack_user_id = slack_user.id
        else:
            logger.warning(
                "Couldn't find slack user for: {}".format(member_model.email)
            )

        self.auth0_client.create_user(member_model.email, member_model.name)

        # Send the new member email
        self.sendgrid_client.send(
            sendgrid.helpers.mail.Mail(
                from_email=self.from_email,
                to_emails=member_model.email,
                subject="Welcome to Bed-Stuy Strong {}!".format(
                    member_model.name
                ),
                html_content=templates.render("new_member_email.html.jinja"),
            )
        )

        member_model.status = "Processed"
