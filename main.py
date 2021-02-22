import logging

from python_http_client.exceptions import BadRequestsError
import sendgrid
import structlog

from automation import cloud_logging, config, tables  # noqa: E402
from automation.functions import delivery


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
    try:
        email = delivery.construct_delivery_email(
            log,
            request,
            intake_table,
            member_table,
        )
    except delivery.DeliveryEmailError as e:
        return e.msg, e.status_code

    email.from_email = conf.sendgrid.from_email
    email.add_cc(conf.sendgrid.reply_to)
    email.reply_to = conf.sendgrid.reply_to

    try:
        sendgrid_client.send(email)
    except BadRequestsError as e:
        msg = f"Error sending email: {e.status_code} {e.reason}"
        log.error(msg, body=e.body, exc_info=True)
        return msg, e.status_code

    msg = "Sent email"
    log.info(msg)
    return msg, 200
