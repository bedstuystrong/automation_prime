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
from typing import Dict, Optional, Set, Type

import pydantic
import pydantic.schema
from pydantic import constr
from airtable import Airtable

from ..secrets import BaseSecret, SecretsClient
from ..settings import BaseConfig

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
                # Exclude _meta so that only the node automation controls it.
                exclude={"id", "created_at", "_meta"},
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


############
# SETTINGS #
############


class AirtableSecrets(BaseSecret):

    _secret_name = "airtable"
    api_key: pydantic.SecretStr


class AirtableSettings(pydantic.BaseSettings):
    base_id: constr(strip_whitespace=True, min_length=1)
    table_names: Dict[str, str]

    class Config(BaseConfig):
        env_prefix = "airtable_"


#########
# TABLE #
#########


class TableSpec(pydantic.BaseModel):
    name: str
    model_cls: Type[BaseModel]

    def get_airtable_client(
        self,
        read_only=False,
        secrets_client=None,
        settings=None,
    ):
        if secrets_client is None:
            secrets_client = SecretsClient()
        if settings is None:
            settings = AirtableSettings()
        return AirtableClient(
            settings.table_names[self.name],
            self,
            read_only,
            secrets_client=secrets_client,
            settings=settings,
        )

    # TODO : add a `status_to_cb` validator that calls `get_valid_statuses`


##########
# CLIENT #
##########


class AirtableClient:
    def __init__(
        self,
        airtable_name,
        table_spec,
        read_only,
        secrets_client=None,
        settings=None,
    ):
        if secrets_client is None:
            secrets_client = SecretsClient()
        if settings is None:
            settings = AirtableSettings()
        secrets = AirtableSecrets.load(secrets_client)
        self.read_only = read_only
        self.client = Airtable(
            settings.base_id, airtable_name, secrets.api_key.get_secret_value()
        )
        self.table_spec = table_spec

    def get(self, record_id):
        raw = self.client.get(record_id)
        return self.table_spec.model_cls.from_airtable(raw)

    def paginate_all(self, formula=None):
        for page in self.client.get_iter(formula=formula):
            page = [
                self.table_spec.model_cls.from_airtable(raw) for raw in page
            ]
            yield page

    def get_all(self, formula=None):
        for page in self.paginate_all(formula=formula):
            yield from page

    def paginate_all_with_new_status(self):
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
        return self.paginate_all(
            formula=(
                "AND({Status} != BLANK(), "
                "{Status} != {_meta_last_seen_status})"
            )
        )

    def get_all_with_new_status(self):
        for page in self.paginate_all_with_new_status():
            yield from page

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
        self, callback, max_num_retries=DEFAULT_POLL_TABLE_MAX_NUM_RETRIES
    ):
        logger.info("Polling table: {}".format(self.table_spec.name))

        success = True

        for record in self.get_all_with_new_status():
            logger.info(
                f"Processing '{self.table_spec.name}' record: {record}"
            )

            if record.status is None:
                logger.error(f"Record {record.id}'s status is None!")
                success = False
                continue

            try:
                original_id = record.id
                original_status = record.status

                for num_retries in range(max_num_retries):
                    try:
                        callback(record)
                        break
                    except Exception:
                        logger.exception(
                            f"Callback for record failed "
                            f"(num retries {num_retries}): {record.id}"
                        )
                else:
                    logger.error(
                        f"Callback for record did not succeed: {record.id}"
                    )
                    success = False

                if original_id != record.id:
                    raise ValueError(
                        f"Callback modified the ID of the "
                        f"record: original={original_id}, new={record.id}"
                    )
            finally:
                record.meta_last_seen_status = original_status

                # Update the record in airtable to reflect local modifications
                self.update(record)

        return success
