from datetime import datetime
from unittest import mock

from hypothesis import given
from hypothesis.strategies import (
    builds,
    characters,
    data,
    emails,
    just,
    shared,
    text,
)

from automation.functions.delivery import (
    Inventory,
    check_ready_to_send,
    render_email_template,
)
from automation.models import IntakeModel, MemberModel


@given(
    data=data(),
    volunteer_id=shared(text(min_size=1), key="volunteer_id"),
)
def test_render_email_template(data, volunteer_id):
    ticket = data.draw(
        builds(
            IntakeModel,
            delivery_volunteer=just([volunteer_id]),
            status=just("Assigned / In Progress"),
            # Make sure none of these are empty, check_ready_to_send should
            # catch that.
            request_name=text(),
            address=text(),
            phone_number=text(),
        )
    )
    volunteer = data.draw(
        builds(
            MemberModel,
            **{
                "id": just(volunteer_id),
                "Name": text(
                    alphabet=characters(
                        whitelist_categories=("L", "Zs"),
                    )
                ),
                "Email Address": emails(),
            },
        )
    )
    inventory = mock.Mock(Inventory, auto_spec=True)
    inventory.category.return_value = "Groceries"
    inventory.quantity.return_value = 1
    inventory.quantity.return_value = "widget"

    email = render_email_template(ticket, [volunteer], inventory)

    # sendgrid's "to" list is weird, it's inside "personalizations" and has an
    # odd format
    to = next(p["to"] for p in email.get()["personalizations"] if "to" in p)
    to_emails = [r["email"] for r in to if "email" in r]
    assert (
        volunteer.email in to_emails
        or f"{volunteer.name} <{volunteer.email}>" in to_emails
    )
    expected_subject = (
        f"[Bed Stuy Strong] Delivery Instructions for {ticket.ticket_id}"
    )
    assert str(email.subject) == expected_subject
    for food_option in ticket.food_options:
        assert food_option in email.content


def test_ready_to_send():
    required = dict(
        id="1",
        created_at=datetime.now(),
        ticket_id="1234",
        recordID="rec1234",
    )
    ticket = IntakeModel(**required, status="Seeking Volunteer")
    problem = check_ready_to_send(ticket)
    assert problem is not None
    ticket.status = "Assigned / In Progress"
    problem = check_ready_to_send(ticket)
    assert problem is not None
    ticket.delivery_volunteer.append("rec5678")
    problem = check_ready_to_send(ticket)
    assert problem is not None
    ticket.request_name = "Fred R"
    problem = check_ready_to_send(ticket)
    assert problem is not None
    ticket.address = "4716 Ellsworth Avenue"
    problem = check_ready_to_send(ticket)
    assert problem is not None
    ticket.phone_number = "611"
    problem = check_ready_to_send(ticket)
    assert problem is None
