import abc
import enum

from typing import *

import pydantic


class BaseModel(pydantic.BaseModel, abc.ABC):
    id: str

    @classmethod
    def from_airtable(cls, raw_dict):
        return cls(id=raw_dict["id"], **raw_dict["fields"])

    def to_airtable(self):
        fields = self.dict(by_alias=True, exclude_none=True)
        del fields["id"]

        return {
            "id": self.id,
            "fields": fields,
        }


# TODO : should this class inheret from ABC?
class MetaBaseModel(BaseModel, abc.ABC):
    meta: Optional[pydantic.Json] = pydantic.Field(default=None, alias="_meta")
    meta_last_seen_status: Optional[str] = pydantic.Field(
        default=None, alias="_meta_last_seen_status"
    )
    status: Optional[str] = pydantic.Field(default=None, alias="Status")

    @staticmethod
    @abc.abstractmethod
    def get_valid_statuses() -> Set[str]:
        ...

    @pydantic.validator("status", allow_reuse=True)
    @pydantic.validator("meta_last_seen_status", allow_reuse=True)
    def validate_status(cls, v):
        valid_statuses = cls.get_valid_statuses()

        if v not in valid_statuses:
            raise ValueError(
                "Status '{}' not in valid statuses: {}".format(
                    v, ", ".join(valid_statuses)
                )
            )

        return v


class InboundModel(MetaBaseModel):
    method: str = pydantic.Field(alias="Method of Contact")
    phoneNumber: Optional[str] = pydantic.Field(alias="Phone Number")
    message: Optional[str] = pydantic.Field(alias="Message")
    voicemailRecording: Optional[str] = pydantic.Field(alias="Voicemail Recording")
    # TODO : intake volunteer shouldn't be one-only
    intakeVolunteer: List[str] = pydantic.Field(
        default_factory=list, alias="Intake Volunteer"
    )
    intakeTime: str = pydantic.Field(alias="Intake Time")
    otherInbounds: List[str] = pydantic.Field(
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
