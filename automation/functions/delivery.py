from requests.exceptions import HTTPError
from sendgrid.helpers.mail import Mail
import structlog
from structlog.contextvars import bind_contextvars

from automation.clients.templates import render


class DeliveryEmailError(Exception):
    """Error constructing delivery email."""

    def __init__(self, msg, status_code):
        self.msg = msg
        self.status_code = status_code


def check_ready_to_send(ticket):
    if ticket.status != "Assigned / In Progress":
        return f"Ticket {ticket.ticket_id} is not assigned"
    if not ticket.delivery_volunteer:
        return f"Ticket {ticket.ticket_id} has no delivery volunteer"
    return None


def render_email_template(ticket, delivery_volunteers):
    message = Mail(
        to_emails=[f"{v.name} <{v.email}>" for v in delivery_volunteers],
        subject=(
            f"[Bed Stuy Strong] Delivery Instructions for {ticket.ticket_id}"
        ),
        html_content=render(
            "delivery_email.html.jinja",
            ticket=ticket,
            delivery_volunteers=delivery_volunteers,
        ),
    )
    return message


def construct_delivery_email(request, intake_table, member_table):
    log = structlog.get_logger("send_delivery_email")
    log.info("Sending delivery email", args=dict(request.args))
    try:
        record_id = request.args["record_id"]
    except KeyError:
        msg = "Must provide record_id"
        log.error(msg)
        raise DeliveryEmailError(msg, 400)
    try:
        ticket = intake_table.get(record_id)
    except HTTPError as e:
        msg = f"Error finding intake ticket: {e.response.text}"
        log.error(msg, exc_info=True)
        raise DeliveryEmailError(msg, e.response.status_code)

    bind_contextvars(ticket_id=ticket.ticket_id)

    problem = check_ready_to_send(ticket)
    if problem:
        msg = "Ticket not ready to send"
        log.error(msg, problem=problem)
        raise DeliveryEmailError(problem, 412)

    delivery_volunteers = []
    for r in ticket.delivery_volunteer:
        try:
            delivery_volunteers.append(member_table.get(r))
        except HTTPError as e:
            msg = f"Error finding delivery volunteer {r}: {e.response.text}"
            log.error(msg, exc_info=True)
            raise DeliveryEmailError(msg, e.response.status_code)

    return render_email_template(ticket, delivery_volunteers)
