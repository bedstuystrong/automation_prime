from sendgrid.helpers.mail import Mail, Email
import structlog

from ..utils import templates

log = structlog.get_logger("poll_members")


def on_new(
    member, *, auth0_client, mailchimp_client, sendgrid_client, slack_client
):
    log.info("on_new")
    # Look up (or create) and store the member's slack metadata
    slack_user = slack_client.users_lookupByEmail(member.email)
    if slack_user is None:
        log.info("Sending Slack invite")
        slack_user = slack_client.users_invite(member.email, member.name)

    member.slack_email = slack_user.profile.email
    member.slack_user_id = slack_user.id

    # Create Auth0 user for Member Hub
    log.info("Creating Auth0 user")
    auth0_client.create_user(member.email, member.name)

    # Subscribe to newsletter
    if "Email" in member.communication_methods:
        mailchimp_client.subscribe(member.email)

    # Send the new member email
    log.info("Sending welcome email")
    subject = "Welcome to Bed-Stuy Strong!"
    message = Mail(
        from_email=Email(
            email="community@mail.bedstuystrong.com", name="Bed-Stuy Strong"
        ),
        to_emails=member.email,
        subject=subject,
        html_content=templates.render(
            "new_member_email.html.jinja",
            inline_css=True,
            subject=subject,
            member=member,
        ),
    )
    message.reply_to = "community@bedstuystrong.com"
    sendgrid_client.send(message)

    member.status = "Processed"
    log.info("on_new completed")
