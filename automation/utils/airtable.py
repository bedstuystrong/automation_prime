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
import logging
from typing import Callable, Dict, Optional, Set, Type

import pydantic

from airtable import Airtable as _AirtableClient

from .. import config

logger = logging.getLogger(__name__)


##########
# CONSTS #
##########

DEFAULT_POLL_TABLE_MAX_NUM_RETRIES = 3


###############
# BASE MODELS #
###############


# TODO : consider not allowing users change the id field
class BaseModel(pydantic.BaseModel, abc.ABC):
    id: str

    class Config:
        allow_population_by_field_name = True

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

    # TODO : add a `status_to_cb` validator that calls `get_valid_statuses`


##########
# CLIENT #
##########


class AirtableClient:
    def __init__(self):
        self._table_name_to_client = {}

    def _get_client(self, table_spec):
        if table_spec.name not in self._table_name_to_client.keys():
            self._table_name_to_client[table_spec.name] = _AirtableClient(
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

        # NOTE here is a formula for querying on a blank status
        # TODO : get rid of this if we don't need it
        # "IF("
        # "{{Status}} = BLANK(),"
        # # If blank...
        # "{{_meta_last_seen_status}} != \"{blank_sentinel}\","
        # # If not blank...
        # "{{Status}} != {{_meta_last_seen_status}}"
        # ")"

        return [
            table_spec.model_cls.from_airtable(raw)
            for raw in self._get_client(table_spec).get_all(
                formula=(
                    "AND({Status} != BLANK(), "
                    "{Status} != {_meta_last_seen_status})"
                )
            )
        ]

    def iter(self, table_spec):
        for page in self._get_client(table_spec).get_iter():
            for raw in page:
                yield table_spec.model_cls.from_airtable(raw)

    def update(self, table_spec, model):
        self._get_client(table_spec).update(
            model.id,
            model.to_airtable()["fields"],
        )


#########
# UTILS #
#########

# TODO : handle missing statuses (e.g. airtable field was updated)
def poll_table(
    client, table_spec, max_num_retries=DEFAULT_POLL_TABLE_MAX_NUM_RETRIES
):
    logger.info("Polling table: {}".format(table_spec.name))

    success = True

    for record in client.poll(table_spec):
        assert record.status is not None

        logger.info(
            "Processing '{}' record: {}".format(table_spec.name, record)
        )

        original_id = record.id
        original_status = record.status

        cb = table_spec.status_to_cb.get(record.status)

        if cb is None:
            logger.info(
                "No callback for record with status '{}': {}".format(
                    record.status,
                    record.id,
                )
            )
            continue

        for num_retries in range(max_num_retries):
            try:
                cb(record)  # noqa: F841
                break
            except Exception:
                logger.exception(
                    (
                        "Callback '{}' for record failed (num retries {}): {}"
                    ).format(
                        num_retries,
                        cb.__qualname__,
                        record.id,
                    )
                )
        else:
            logger.error(
                "Callback '{}' for record did not succeed: {}".format(
                    cb.__qualname__, record.id
                )
            )
            success = False

        if original_id != record.id:
            raise ValueError(
                (
                    "Callback '{}' modified the ID of the record: "
                    "original={}, new={}"
                ).format(
                    cb.__qualname__,
                    original_id,
                    record.id,
                )
            )

        record.meta_last_seen_status = original_status

        # Update the record in airtable to reflect local modifications
        client.update(table_spec, record)

    return success
