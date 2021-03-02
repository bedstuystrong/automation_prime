from datetime import datetime
from unittest import mock

from hypothesis import given
from hypothesis.strategies import (
    booleans,
    builds,
    characters,
    data,
    emails,
    lists,
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
    allow_empty_food_options=booleans(),
    allow_empty_other_items=booleans(),
)
def test_render_email_template(
    data, volunteer_id, allow_empty_food_options, allow_empty_other_items
):
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
            food_options=lists(
                text(), min_size=0 if allow_empty_food_options else 1
            ),
            other_items=text(min_size=0 if allow_empty_other_items else 1),
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
    inventory.unit.return_value = "widget"

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
    for content in email.contents:
        for food_option in ticket.food_options:
            assert food_option in content.content
        if ticket.other_items is not None:
            for item in ticket.other_items.split(","):
                assert item.strip() in content.content
        for field in (
            ticket.request_name,
            ticket.address,
            ticket.phone_number,
        ):
            assert field in content.content


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
