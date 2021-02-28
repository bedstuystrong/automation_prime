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
import datetime
import json
import logging
from typing import Callable, Dict, Optional, Set, Type

import pydantic
from airtable import Airtable

from automation.config import AirtableConfig

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
    id: str = pydantic.Field(allow_mutation=False)
    created_at: datetime.datetime = pydantic.Field(allow_mutation=False)

    _snapshot = pydantic.PrivateAttr(default=None)

    class Config:
        allow_population_by_field_name = True
        underscore_attrs_are_private = True
        validate_assignment = True

    def snapshot(self):
        self._snapshot = self.copy(deep=True)

    def get_modified_fields(self):
        if self._snapshot is None:
            raise RuntimeError(
                "Attempted to get modified fields without having taken a "
                "snapshot"
            )

        snapshot_dict = self._snapshot.dict()
        self_dict = self.dict()
        all_fields = snapshot_dict.keys() | self_dict.keys()

        modified_fields = set()
        for field in all_fields:
            if snapshot_dict.get(field) != self_dict.get(field):
                modified_fields.add(field)

        return modified_fields

    @classmethod
    def from_airtable(cls, raw_dict):
        model = cls(
            id=raw_dict["id"],
            created_at=raw_dict["createdTime"],
            **raw_dict["fields"],
        )
        model.snapshot()
        return model

    def to_airtable(self, modified_only=False):
        include = None
        if modified_only:
            include = self.get_modified_fields()

        # NOTE that `pydantic.BaseModel.dict()` doesn't serialize all types to
        # strings, so we have to use `pydantic.BaseModel.json()` to dump the
        # model to json and then reload it back into a dict.
        fields = json.loads(
            self.json(
                by_alias=True,
                exclude_none=True,
                include=include,
                exclude={"id", "created_at"},
            )
        )

        return {
            "id": self.id,
            "fields": fields,
        }


# TODO : should this class inherit from ABC?
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

    def get_airtable_client(self, conf: AirtableConfig, read_only=False):
        return AirtableClient(
            conf, conf.table_names[self.name], self, read_only
        )

    # TODO : add a `status_to_cb` validator that calls `get_valid_statuses`


##########
# CLIENT #
##########


class AirtableClient:
    def __init__(
        self, conf: AirtableConfig, airtable_name, table_spec, read_only
    ):
        self.read_only = read_only
        self.client = Airtable(
            conf.base_id,
            airtable_name,
            conf.api_key,
        )
        self.table_spec = table_spec

    def get_all(self, formula=None):
        return (
            self.table_spec.model_cls.from_airtable(raw)
            for page in self.client.get_iter(formula=formula)
            for raw in page
        )

    def get_all_with_new_status(self):
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

        return self.get_all(
            formula=(
                "AND({Status} != BLANK(), "
                "{Status} != {_meta_last_seen_status})"
            )
        )

    def update(self, model):
        if self.read_only:
            logger.info(f"Not updating {model.id} in read-only mode")
            return

        self.client.update(
            model.id,
            model.to_airtable(modified_only=True)["fields"],
        )

        # Airtable record has been updated, take a new snapshot
        model.snapshot()

    # TODO : handle missing statuses (e.g. airtable field was updated)
    def poll_table(
        self, conf, max_num_retries=DEFAULT_POLL_TABLE_MAX_NUM_RETRIES
    ):
        logger.info("Polling table: {}".format(self.table_spec.name))

        success = True

        callbacks = {
            status: cb(conf)
            for status, cb in self.table_spec.status_to_cb.items()
        }

        for record in self.get_all_with_new_status():
            assert record.status is not None

            logger.info(
                f"Processing '{self.table_spec.name}' record: {record}"
            )

            try:
                original_id = record.id
                original_status = record.status

                cb = callbacks.get(record.status)

                if cb is None:
                    logger.info(
                        "No callback for record with status "
                        f"'{record.status}': {record.id}"
                    )
                    continue

                for num_retries in range(max_num_retries):
                    try:
                        cb(record)  # noqa: F841
                        break
                    except Exception:
                        logger.exception(
                            f"Callback '{type(cb).__name__}' for record "
                            f"failed (num retries {num_retries}): {record.id}"
                        )
                else:
                    logger.error(
                        f"Callback '{type(cb).__name__}' for record did not "
                        f"succeed: {record.id}"
                    )
                    success = False

                if original_id != record.id:
                    raise ValueError(
                        f"Callback '{type(cb).__name__}' modified the ID of "
                        f"the record: original={original_id}, new={record.id}"
                    )
            finally:
                record.meta_last_seen_status = original_status

                # Update the record in airtable to reflect local modifications
                self.update(record)

        return success
