from python_http_client.exceptions import BadRequestsError
from requests.exceptions import HTTPError
from sendgrid.helpers.mail import Mail
import structlog
from structlog.contextvars import bind_contextvars

from automation.utils.templates import render

log = structlog.get_logger("send_delivery_email")

# Turn this off for debugging
SEND_MAIL = True


def on_assigned(
    ticket,
    *,
    member_table,
    inventory,
    sendgrid_client,
    from_email,
    reply_to=None,
):
    bind_contextvars(ticket_id=ticket.ticket_id)
    log.info("Sending delivery email")

    problem = check_ready_to_send(ticket)
    if problem:
        msg = "Ticket not ready to send"
        log.error(msg, problem=problem)
        return

    delivery_volunteers = get_delivery_volunteers(ticket, member_table)
    email = render_email_template(ticket, delivery_volunteers, inventory)
    email.from_email = from_email
    if reply_to:
        email.add_cc(reply_to)
        email.reply_to = reply_to

    if not SEND_MAIL:
        log.info(
            "Would send email", to=email.get()["personalizations"][0]["to"]
        )
        return
    try:
        sendgrid_client.send(email)
        log.info("Sent email")
    except BadRequestsError as e:
        msg = f"Error sending email: {e.status_code} {e.reason}"
        log.error(msg, body=e.body, exc_info=True)
        raise DeliveryEmailError(msg)


def check_ready_to_send(ticket):
    if ticket.status != "Assigned / In Progress":
        return f"Ticket {ticket.ticket_id} is not assigned"
    if not ticket.delivery_volunteer:
        return f"Ticket {ticket.ticket_id} has no delivery volunteer"
    if not ticket.request_name:
        return f"Ticket {ticket.ticket_id} has no requester name"
    if not ticket.address:
        return f"Ticket {ticket.ticket_id} has no address"
    if not ticket.phone_number:
        return f"Ticket {ticket.ticket_id} has no phone number"
    return None


def get_delivery_volunteers(ticket, member_table):
    delivery_volunteers = []
    for r in ticket.delivery_volunteer:
        try:
            delivery_volunteers.append(member_table.get(r))
        except HTTPError as e:
            msg = f"Error finding delivery volunteer {r}: {e.response.text}"
            log.error(msg, exc_info=True)
            raise DeliveryEmailError(msg)

    return delivery_volunteers


def render_email_template(ticket, delivery_volunteers, inventory):
    shopping_list = [
        {
            "name": item,
            "category": inventory.category(item),
            "quantity": inventory.quantity(item, ticket.household_size),
            "unit": inventory.unit(item),
        }
        for item in ticket.food_options
    ]
    message = Mail(
        to_emails=[f"{v.name} <{v.email}>" for v in delivery_volunteers],
        subject=(
            f"[Bed Stuy Strong] Delivery Instructions for {ticket.ticket_id}"
        ),
        html_content=render(
            "delivery_email.html.jinja",
            ticket=ticket,
            delivery_volunteers=delivery_volunteers,
            shopping_list=shopping_list,
        ),
    )
    return message


class Inventory:
    def __init__(self, items_by_household_size_table):
        self.categories = {}
        self.quantities = {}
        self.units = {}
        for record in items_by_household_size_table.get_all(
            '{Category} != "Children / Babies"'
        ):
            self.categories[record.item] = record.category
            self.quantities[record.item] = [
                0,
                record.size_1,
                record.size_2,
                record.size_3,
                record.size_4,
                record.size_5,
                record.size_6,
                record.size_7,
                record.size_8,
                record.size_9,
                record.size_10,
            ]
            self.units[record.item] = record.unit

    def category(self, item):
        return self.categories[item]

    def quantity(self, item, household_size):
        return self.quantities[item][household_size]

    def unit(self, item):
        return self.units[item]


class DeliveryEmailError(Exception):
    """Error constructing delivery email."""


if __name__ == "__main__":
    from automation import config, tables
    import sendgrid
    import sys

    if len(sys.argv) != 2:
        sys.exit("Usage: python -m automation.functions.delivery <ticket ID>")

    conf = config.load()
    intake = tables.Intake.get_airtable(conf.airtable, read_only=True)
    try:
        ticket = next(
            intake.get_all(formula=f'{{Ticket ID}} = "{sys.argv[1]}"')
        )
    except StopIteration:
        sys.exit(f"Ticket {sys.argv[1]} not found!")
    members = tables.Members.get_airtable(conf.airtable, read_only=True)
    volunteers = [members.get(v) for v in ticket.delivery_volunteer]
    ibhs = tables.ITEMS_BY_HOUSEHOLD_SIZE.get_airtable_client(
        conf.airtable, read_only=True
    )
    inventory = Inventory(ibhs)
    sendgrid_client = sendgrid.SendGridAPIClient(conf.sendgrid.api_key)
    on_assigned(
        ticket,
        member_table=members,
        inventory=inventory,
        sendgrid_client=sendgrid_client,
        from_email=conf.sendgrid.from_email,
    )
    # print(mail.get()["content"][0]["value"])
