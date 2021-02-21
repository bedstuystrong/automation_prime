from datetime import date
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


class IntakeModel(MetaBaseModel):
    ticket_id: str = pydantic.Field(alias="Ticket ID")
    intake_volunteer: List[str] = pydantic.Field(
        alias="Intake Volunteer - This is you!", default_factory=list
    )
    delivery_volunteer: List[str] = pydantic.Field(
        alias="Delivery Volunteer", default_factory=list
    )
    neighborhood: Optional[str] = pydantic.Field(alias="Neighborhood")
    request_name: Optional[str] = pydantic.Field(
        alias="Requestor First Name and Last Initial"
    )
    nearest_intersection: Optional[str] = pydantic.Field(
        alias="Nearest Intersection"
    )
    language: List[str] = pydantic.Field(
        alias="Language", default_factory=list
    )
    address: Optional[str] = pydantic.Field(
        alias="Address (won't post in Slack)"
    )
    phone_number: Optional[str] = pydantic.Field(alias="Phone Number")
    vulnerability: List[str] = pydantic.Field(
        alias="Vulnerability", default_factory=list
    )
    household_size: Optional[int] = pydantic.Field(alias="Household Size")
    delivery_notes: Optional[str] = pydantic.Field(
        alias="Notes for Delivery Volunteer (won't post in Slack)"
    )
    food_options: List[str] = pydantic.Field(
        alias="Food Options", default_factory=list
    )
    other_items: Optional[str] = pydantic.Field(alias="Other Items")
    recordID: str = pydantic.Field(alias="record ID")
    date_completed: Optional[date] = pydantic.Field(alias="Completion_Date")
    can_meet_outside: Optional[bool] = pydantic.Field(alias="Can meet outside")

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
