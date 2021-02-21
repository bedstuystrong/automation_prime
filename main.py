import logging

from python_http_client.exceptions import BadRequestsError
from requests.exceptions import HTTPError
import sendgrid

from automation import config, tables  # noqa: E402
from automation.functions.delivery import (
    check_ready_to_send,
    render_email_template,
)

logging.basicConfig(level=logging.INFO)


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################

conf = config.load()


def poll_members(event, context):
    client = tables.MEMBERS.get_airtable_client(conf.airtable)
    success = client.poll_table(conf)
    logging.info("Polling complete" if success else "Polling failed")


intake_table = tables.INTAKE.get_airtable_client(conf.airtable)
member_table = tables.MEMBERS.get_airtable_client(conf.airtable)
sendgrid_client = sendgrid.SendGridAPIClient(conf.sendgrid.api_key)


def send_delivery_email(request):
    log = logging.getLogger("send_delivery_email")
    try:
        record_id = request.args["record_id"]
    except KeyError:
        return "Must provide record_id", 400
    try:
        ticket = intake_table.get(record_id)
    except HTTPError as e:
        return (
            f"Error finding intake ticket: {e.response.text}",
            e.response.status_code,
        )

    problem = check_ready_to_send(ticket)
    if problem:
        return problem, 412

    delivery_volunteers = []
    for r in ticket.delivery_volunteer:
        try:
            delivery_volunteers.append(member_table.get(r))
        except HTTPError as e:
            return (
                f"Error finding delivery volunteer {r}: {e.response.text}",
                e.response.status_code,
            )

    email = render_email_template(ticket, delivery_volunteers)
    email.from_email = conf.sendgrid.from_email
    email.add_cc(conf.sendgrid.reply_to)
    email.reply_to = conf.sendgrid.reply_to

    try:
        sendgrid_client.send(email)
    except BadRequestsError as e:
        log.error(
            f"Error sending email: {e.status_code} {e.reason}", exc_info=True
        )
        return f"Error sending email: {e.reason}", e.status_code

    return f"Sending {email.subject}", 200
