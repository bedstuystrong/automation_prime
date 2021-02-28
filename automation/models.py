import enum
from typing import List, Optional

import pydantic

from .clients.airtable import MetaBaseModel


class InboundModel(MetaBaseModel):
    method: Optional[str] = pydantic.Field(alias="Method of Contact")
    phone_number: Optional[str] = pydantic.Field(alias="Phone Number")
    message: Optional[str] = pydantic.Field(alias="Message")
    voicemail_recording: Optional[str] = pydantic.Field(
        alias="Voicemail Recording"
    )
    # TODO : intake member shouldn't be one-only
    intake_member: List[str] = pydantic.Field(
        default_factory=list, alias="Intake Member"
    )
    intake_time: str = pydantic.Field(alias="Intake Time")
    other_inbounds: List[str] = pydantic.Field(
        default_factory=list, alias="Other Inbounds"
    )

    @staticmethod
    def get_valid_statuses():
        return {
            "Intake Needed",
            "In Progress",
            "Intake Complete",
            "Duplicate",
            "Outside Bed-Stuy",
            "Call Back",
            "Question/Info",
            "Thank you!",
            "Spanish-Intake needed",
            "No longer needs assistance",
            "Phone Tag",
            "Out of Service/Cannot Reach",
        }

    @classmethod
    def get_nonterminal_statuses(cls):
        NONTERMINAL_STATUSES = {
            "Intake Needed",
            "In Progress",
            "Call Back",
            "Spanish-Intake needed",
        }

        invalid_statuses = NONTERMINAL_STATUSES - cls.get_valid_statuses()
        if len(invalid_statuses) != 0:
            raise ValueError(
                "One or more nonterminal statuses are invalid: {}".format(
                    ", ".join(invalid_statuses)
                )
            )

        return NONTERMINAL_STATUSES

    @classmethod
    def get_terminal_statuses(cls):
        return cls.get_valid_statuses() - cls.get_nonterminal_statuses()

    @pydantic.validator("method")
    def validate_method(cls, v):
        if v not in {"Email", "Phone Call", "Text Message"}:
            raise ValueError("Invalid method value: {}".format(v))


class MemberModel(MetaBaseModel):
    name: str = pydantic.Field(alias="Name")
    # TODO : fix data quality issues and make this non-optional
    email: Optional[str] = pydantic.Field(alias="Email Address")
    phone_number: Optional[str] = pydantic.Field(alias="Phone Number")
    # TODO : this is the only slack handle field that matters, remove the
    # old one
    slack_handle: Optional[str] = pydantic.Field(
        alias="Slack Handle (Derived)"
    )
    slack_email: Optional[str] = pydantic.Field(
        alias="Email Address (from Slack)"
    )
    slack_user_id: Optional[str] = pydantic.Field(alias="Slack User ID")
    intake_tickets: List[str] = pydantic.Field(
        alias="Intake Member tickets", default_factory=list
    )
    delivery_tickets: List[str] = pydantic.Field(
        alias="Delivery Member tickets",
        default_factory=list,
    )

    def get_email(self) -> Optional[str]:
        return self.email if self.email is not None else self.slack_email

    @staticmethod
    def get_valid_statuses():
        return {
            "New",
            "Processed",
        }


class IntakeTicketModel(MetaBaseModel):
    ticket_id: str = pydantic.Field(alias="Ticket ID")
    requestor: str = pydantic.Field(
        alias="Requestor First Name and Last Initial"
    )
    status: str = pydantic.Field(alias="Status")
    phone_number: str = pydantic.Field(alias="Phone Number")
    vulnerability: List[str] = pydantic.Field(
        alias="Vulnerability", default_factory=list
    )

    @staticmethod
    def get_valid_statuses():
        return {
            "Seeking Volunteer",
            "Assigned / In Progress",
            "Complete",
            "Not Bed-Stuy",
            "Assistance No Longer Required",
            "Cannot Reach / Out of Service",
            "Bulk Delivery Scheduled",
            "Bulk Delivery Confirmed",
            "AC Needed",
            "AC Delivered",
            "Seeking Other Goods",
        }


class AdministrativeModel(MetaBaseModel):
    class Names(enum.Enum):
        MAXIMUM_CAPACITY = "Maximum Capacity"
        MINIMUM_CAPACITY = "Minimum Capacity"
        INBOUND_BACKLOG = "Inbound Backlog"
        DELIVERY_BACKLOG_UNASSIGNED = "Delivery Backlog (Unassigned)"
        DELIVERY_BACKLOG_IN_PROGRESS = "Delivery Backlog (In Progress)"

    name: Names = pydantic.Field(alias="Name")
    value: Optional[int] = pydantic.Field(alias="Value")

    @staticmethod
    def get_valid_statuses():
        return {
            "Update Needed",
            "Updated",
            "Override",
            "Manual",
        }
