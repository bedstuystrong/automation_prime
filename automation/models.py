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
