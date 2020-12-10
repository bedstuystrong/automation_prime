from typing import List, Optional

import pydantic

from .utils.airtable import MetaBaseModel


class InboundModel(MetaBaseModel):
    method: str = pydantic.Field(alias="Method of Contact")
    phone_number: Optional[str] = pydantic.Field(alias="Phone Number")
    message: Optional[str] = pydantic.Field(alias="Message")
    voicemail_recording: Optional[str] = pydantic.Field(
        alias="Voicemail Recording"
    )
    # TODO : intake volunteer shouldn't be one-only
    intake_volunteer: List[str] = pydantic.Field(
        default_factory=list, alias="Intake Volunteer"
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
