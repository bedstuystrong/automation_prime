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
import enum
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


class BaseModelState(enum.Enum):
    NEW = "NEW"
    """Newly created locally, not yet saved remotely"""

    CLEAN = "CLEAN"
    """Loaded or saved from remote, unmodified locally"""

    DIRTY = "DIRTY"
    """Contains local modifications, not yet updated remotely"""


class BaseModel(pydantic.BaseModel, abc.ABC):
    id: Optional[str] = pydantic.Field(...)
    """The identifier of the record, always `None` if `state == New`"""
    created_at: Optional[datetime.datetime] = pydantic.Field(...)
    """Creation time of the record, always `None` if `state == New`"""

    # NOTE that state must be initialized after `id` and `created_at`
    state: BaseModelState
    """Current state of the model"""

    last_snapshot: Optional["BaseModel"] = pydantic.Field(default=None)
    """Last snapshot taken after loading or saving to remote

    Used to determine modified fields that need to be saved on the remote
    """

    modified_fields: Optional[Set[str]] = pydantic.Field(default=None)
    """Contains a set of modified field names, automatically updated after
    modifying a field
    """

    class Config:
        allow_population_by_field_name = True
        underscore_attrs_are_private = True
        validate_assignment = True

    def __init__(self, **data):
        if "state" not in data:
            raise RuntimeError(
                "Base model must be initialized with a state. NOTE do not use "
                "constructor directly; use factory methods instead."
            )

        if "last_snapshot" in data:
            raise RuntimeError(
                "Base model should not be initialized with 'last_snapshot'"
            )

        if "modified_fields" in data:
            raise RuntimeError(
                "Base model should not be initialized with 'modified_fields'"
            )

        super().__init__(**data)
        # NOTE that our initial snapshot won't capture any modifications that
        # happened during initialization (e.g. via a pydantic validator in
        # a subclass)
        #
        # TODO : consider snapshotting `data` directly
        self.snapshot()

    @pydantic.root_validator()
    def validate_state_invariants(cls, values):
        """Validates and modifies state invariants"""
        cur_state = values["state"]

        if (
            cur_state == BaseModelState.CLEAN
            or cur_state == BaseModelState.DIRTY
        ):
            if values["id"] is None:
                raise ValueError(
                    "Models in 'CLEAN' or 'DIRTY' state must have an 'id'"
                )

            if values["created_at"] is None:
                raise ValueError(
                    "Models in 'CLEAN' or 'DIRTY' state must have an "
                    "'created_at'"
                )

        # Check to see if any fields have changed since the last snapshot,
        # and update `state` and `modified_fields`
        if (
            cur_state != BaseModelState.NEW
            and (last_snapshot := values.get("last_snapshot")) is not None
        ):
            modified_fields = values["modified_fields"]

            snapshot_dict = last_snapshot.dict()
            # NOTE that we exclude any fields in `BaseModel` when checking for
            # modified fields
            relevant_fields = (
                snapshot_dict.keys() | values.keys()
            ) - BaseModel.__fields__.keys()
            modified_fields = {
                field
                for field in relevant_fields
                if snapshot_dict.get(field) != values.get(field)
            }

            if len(modified_fields) != 0:
                values["state"] = BaseModelState.DIRTY
                values["modified_fields"] = modified_fields
            else:
                values["state"] = BaseModelState.CLEAN
                values["modified_fields"] = set()

        return values

    @pydantic.validator("id", "created_at")
    def validate_assignment(cls, v, /, field, values):
        """Validates assignments to `id` and `created_at`"""
        # NOTE that `state` is initialized after `id` and `created_at`
        if values.get("state") is None:
            return v

        if v is not None and values["state"] != BaseModelState.NEW:
            raise ValueError(
                f"Field '{field.name}' may only be set when state is 'NEW' "
                f"(current state): {values['state']}"
            )

        return v

    # METHODS

    def snapshot(self):
        """Takes a snapshot of the model's current state"""
        self.last_snapshot = self.copy(deep=True)
        self.modified_fields = set()

    # (DE)SERIALIZATION METHODS

    @classmethod
    def from_airtable(cls, **raw_dict):
        """Load a model from raw airtable data"""
        res = cls(
            state=BaseModelState.CLEAN,
            id=raw_dict["id"],
            created_at=raw_dict["createdTime"],
            **raw_dict["fields"],
        )
        res.snapshot()
        return res

    @classmethod
    def new(cls, **data):
        """Create a new model from provided data"""
        if (
            len(
                invalid_field_names := (
                    BaseModel.__fields__.keys() & data.keys()
                )
            )
            != 0
        ):
            raise RuntimeError(
                "Provided data contains invalid fields: "
                + ", ".join(invalid_field_names)
            )

        return cls(
            state=BaseModelState.NEW,
            id=None,
            created_at=None,
            **data,
        )

    def to_airtable(self, modified_only=False):
        """Serialize model to airtable format"""
        include = None
        if modified_only:
            include = self.modified_fields

        # NOTE that `pydantic.BaseModel.dict()` doesn't serialize all types to
        # strings, so we have to use `pydantic.BaseModel.json()` to dump the
        # model to json and then reload it back into a dict.
        fields = json.loads(
            self.json(
                by_alias=True,
                exclude_none=True,
                include=include,
                # TODO : once old automation is deprecated, remove `_meta` from
                # `exclude`
                #
                # Exclude _meta so that only the node automation controls it.
                exclude={
                    "state",
                    "id",
                    "created_at",
                    "last_snapshot",
                    "modified_fields",
                    "_meta",
                },
            )
        )

        return {
            "id": self.id,
            "fields": fields,
        }


BaseModel.update_forward_refs()


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


class IncompatibleModelStateError(Exception):
    """Thrown when client operation is not compatible with model state"""


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
        return self.table_spec.model_cls.from_airtable(**raw)

    def paginate_all(self, formula=None):
        for page in self.client.get_iter(formula=formula):
            page = [
                self.table_spec.model_cls.from_airtable(**raw) for raw in page
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

    def insert(self, model):
        if self.read_only:
            logger.info(f"Not inserting {model.id} in read-only mode")
            return

        if model.state != BaseModelState.NEW:
            raise IncompatibleModelStateError(
                f"Cannot insert model in '{model.state}' state, must be "
                "in 'NEW' state"
            )

        res = self.client.insert(
            model.to_airtable()["fields"],
        )

        model.id = res["id"]
        model.created_at = res["createdTime"]

        # Airtable record has been created, take a new snapshot
        model.snapshot()
        model.state = BaseModelState.CLEAN

    def update(self, model):
        if self.read_only:
            logger.info(f"Not updating model '{model.id}' in read-only mode")
            return

        if model.state == BaseModelState.NEW:
            raise IncompatibleModelStateError(
                "Cannot update a model in 'NEW' state"
            )
        elif model.state == BaseModelState.CLEAN:
            logger.debug("Provided model in 'CLEAN' state, skipping update.")
            return
        elif model.state == BaseModelState.DIRTY:
            pass
        else:
            raise RuntimeError(f"Unknown model state: {model.state}")

        self.client.update(
            model.id,
            model.to_airtable(modified_only=True)["fields"],
        )

        # Airtable record has been updated, take a new snapshot
        model.snapshot()
        model.state = BaseModelState.CLEAN

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
