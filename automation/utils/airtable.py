"""Tools for interacting with airtable

Includes:
- Base models, for creating classes from airtable records
- "Meta" base models
    + Track the record's status field
    + Additional JSON metadata for the automation
- Table specs for associating models, table names, and misc
- A table poller for executing callbacks on status changes

"""

import abc
import enum
import logging
from typing import *

import pydantic

from airtable import Airtable

from .. import config


##############
# BASE MODEL #
##############


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


#########
# TABLE #
#########


class TableSpec(pydantic.BaseModel):
    name: str
    model_cls: Type[BaseModel]
    status_to_cb: Dict[Optional[str], Callable[[BaseModel], BaseModel]]

    def get_airtable_name(self):
        return config.Config.load().airtable.table_names[self.name]


##########
# CLIENT #
##########


class Client:
    def __init__(self):
        self._table_name_to_client = {}

    def _get_client(self, table_spec):
        if table_spec.name not in self._table_name_to_client.keys():
            self._table_name_to_client[table_spec.name] = Airtable(
                config.Config.load().airtable.base_id,
                table_spec.get_airtable_name(),
                config.Config.load().airtable.api_key,
            )

        return self._table_name_to_client[table_spec.name]

    def get_all(self, table_spec, formula=None):
        return [
            table_spec.model_cls.from_airtable(raw)
            for raw in self._get_client(table_spec).get_all(formula=formula)
        ]

    def poll(self, table_spec):
        # TODO : sort by creation time asc
        return [
            table_spec.model_cls.from_airtable(raw)
            for raw in self._get_client(table_spec).get_all(
                formula=(
                    "OR({Status} != {_meta_last_seen_status}, "
                    "AND({Status} = BLANK(), {_meta_last_seen_status} = BLANK()))"
                )
            )
        ]

    def iter(self, table_spec):
        for page in self._get_client(table_spec).get_iter():
            for raw in page:
                yield table_spec.model_cls.from_airtable(raw)


#########
# UTILS #
#########

# TODO : handle missing statuses (e.g. airtable field was updated)
def poll_table(table_spec):
    client = Client()

    success = True

    for record in client.poll(table_spec):
        cb = table_spec.status_to_cb.get(record.status)

        if cb is not None:
            original = record.copy(deep=True)

            try:
                new = cb(record)
            except Exception:
                logging.exception(
                    "Callback '{}' for the following record failed: {}".format(
                        cb.__qualname__,
                        record,
                    )
                )
                success = False

            # TODO : update record if dirty

    return success