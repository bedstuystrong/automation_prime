import logging

from python_http_client.exceptions import BadRequestsError
from requests.exceptions import HTTPError
import sendgrid
import structlog
from structlog.contextvars import bind_contextvars

from automation import cloud_logging, config, tables  # noqa: E402
from automation.functions.delivery import (
    check_ready_to_send,
    render_email_template,
)


cloud_logging.configure()
conf = config.load()


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################


def poll_members(event, context):
    client = tables.MEMBERS.get_airtable_client(conf.airtable)
    success = client.poll_table(conf)
    logging.info("Polling complete" if success else "Polling failed")


intake_table = tables.INTAKE.get_airtable_client(conf.airtable)
member_table = tables.MEMBERS.get_airtable_client(conf.airtable)
sendgrid_client = sendgrid.SendGridAPIClient(conf.sendgrid.api_key)


def send_delivery_email(request):
    log = structlog.get_logger("send_delivery_email")
    cloud_logging.bind_trace_id(request, conf.google_cloud.project_id)
    log.info("Sending delivery email", args=dict(request.args))
    try:
        record_id = request.args["record_id"]
    except KeyError:
        return "Must provide record_id", 400
    try:
        ticket = intake_table.get(record_id)
    except HTTPError as e:
        msg = f"Error finding intake ticket: {e.response.text}"
        log.error(msg, exc_info=True)
        return msg, e.response.status_code

    bind_contextvars(ticket_id=ticket.ticket_id)

    problem = check_ready_to_send(ticket)
    if problem:
        log.error("Ticket not ready to send", problem=problem)
        return problem, 412

    delivery_volunteers = []
    for r in ticket.delivery_volunteer:
        try:
            delivery_volunteers.append(member_table.get(r))
        except HTTPError as e:
            msg = f"Error finding delivery volunteer {r}: {e.response.text}"
            log.error(msg, exc_info=True)
            return msg, e.response.status_code

    email = render_email_template(ticket, delivery_volunteers)

    email.from_email = conf.sendgrid.from_email
    email.add_cc(conf.sendgrid.reply_to)
    email.reply_to = conf.sendgrid.reply_to

    try:
        sendgrid_client.send(email)
    except BadRequestsError as e:
        msg = f"Error sending email: {e.status_code} {e.reason}"
        log.error(msg, body=e.body, exc_info=True)
        return msg, e.status_code

    msg = f"Sent email for {ticket.ticket_id}"
    log.info(msg)
    return msg, 200
