import logging

from sendgrid.helpers.mail import Mail

from ..utils import templates

logger = logging.getLogger(__name__)


def on_new(member, *, slack_client, sendgrid_client, auth0_client, from_email):
    # Look up and store the member's slack metadata
    slack_user = slack_client.users_lookupByEmail(member.email)
    if slack_user is None:
        slack_user = slack_client.users_invite(member.email, member.name)

    member.slack_handle = slack_user.get_handle()
    member.slack_email = slack_user.profile.email
    member.slack_user_id = slack_user.id

    # Create Auth0 user for Member Hub
    auth0_client.create_user(member.email, member.name)

    # Send the new member email
    sendgrid_client.send(
        Mail(
            from_email=from_email,
            to_emails=member.email,
            subject="Welcome to Bed-Stuy Strong {}!".format(member.name),
            html_content=templates.render("new_member_email.html.jinja"),
        )
    )

    member.status = "Processed"
