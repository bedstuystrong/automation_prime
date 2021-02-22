from types import SimpleNamespace
from unittest import mock

from hypothesis import given, settings
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
    construct_delivery_email,
    render_email_template,
)
from automation.models import IntakeModel, MemberModel


@settings(max_examples=1000)
@given(
    data=data(),
    volunteer_id=shared(text(min_size=1), key="volunteer_id"),
)
def test_construct_delivery_email(data, volunteer_id):
    ticket = data.draw(
        builds(
            IntakeModel,
            delivery_volunteer=just([volunteer_id]),
            status=just("Assigned / In Progress"),
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
    request = SimpleNamespace(args={"record_id": ticket.id})
    intake_table = mock.Mock()
    intake_table.get = mock.Mock(return_value=ticket)
    member_table = mock.Mock()
    member_table.get = mock.Mock(return_value=volunteer)

    email = construct_delivery_email(request, intake_table, member_table)

    intake_table.get.assert_called_once_with(ticket.id)
    member_table.get.assert_called_once_with(volunteer.id)

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


@settings(max_examples=1000)
@given(
    ticket=builds(
        IntakeModel,
        status=just("Assigned / In Progress"),
    ),
    volunteer=builds(
        MemberModel,
        **{
            "Name": text(
                alphabet=characters(
                    whitelist_categories=("L", "Zs"),
                )
            ),
            "Email Address": emails(),
        },
    ),
)
def test_render_delivery_email(ticket, volunteer):
    email = render_email_template(ticket, [volunteer])

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
