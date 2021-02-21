from automation.clients.templates import render
from sendgrid.helpers.mail import Mail


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
