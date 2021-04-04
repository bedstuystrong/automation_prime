import abc
from functools import cached_property

from . import models
from .functions import delivery, inbound, members
from .clients import airtable, auth0, sendgrid, slack
from .secrets import SecretsClient


class PollableTable(abc.ABC):

    table_spec = ...

    def __init__(
        self,
        read_only=False,
        *,
        secrets_client=SecretsClient(),
        airtable_settings=airtable.AirtableSettings(),
        auth0_settings=auth0.Auth0Settings(),
        slack_settings=slack.SlackSettings(),
        delivery_settings=delivery.DeliverySettings(),
    ):
        self.read_only = read_only
        self.secrets_client = secrets_client
        self.airtable_settings = airtable_settings
        self.auth0_settings = auth0_settings
        self.slack_settings = slack_settings
        self.delivery_settings = delivery_settings

    @classmethod
    def get_airtable(
        cls,
        read_only=False,
        secrets_client=SecretsClient(),
        settings=airtable.AirtableSettings(),
    ):
        return cls.table_spec.get_airtable_client(
            read_only=read_only,
            secrets_client=secrets_client,
            settings=settings,
        )

    def poll_table(self):
        client = self.get_airtable(
            self.read_only,
            secrets_client=self.secrets_client,
            settings=self.airtable_settings,
        )
        return client.poll_table(self.on_status_update)

    @abc.abstractmethod
    def on_status_update(self, record):
        ...


class SlackMixin:
    @cached_property
    def slack_client(self):
        return slack.SlackClient(
            secrets_client=self.secrets_client, settings=self.slack_settings
        )


class EmailMixin:
    @cached_property
    def sendgrid_client(self):
        return sendgrid.SendgridClient(secrets_client=self.secrets_client)


class Auth0Mixin:
    @cached_property
    def auth0_client(self):
        return auth0.Auth0Client(
            secrets_client=self.secrets_client, settings=self.auth0_settings
        )


class Inbound(PollableTable):

    table_spec = airtable.TableSpec(
        name="inbound",
        model_cls=models.InboundModel,
    )

    def on_status_update(self, record):
        inbound.on_new(record)


class Members(PollableTable, SlackMixin, EmailMixin, Auth0Mixin):

    table_spec = airtable.TableSpec(
        name="members",
        model_cls=models.MemberModel,
    )

    def on_status_update(self, record):
        if record.status == "New":
            members.on_new(
                record,
                slack_client=self.slack_client,
                sendgrid_client=self.sendgrid_client,
                auth0_client=self.auth0_client,
            )


class Intake(PollableTable, EmailMixin):

    table_spec = airtable.TableSpec(
        name="intake",
        model_cls=models.IntakeModel,
    )

    @cached_property
    def member_table(self):
        return Members.get_airtable(self.conf.airtable, self.read_only)

    @cached_property
    def inventory(self):
        items = ITEMS_BY_HOUSEHOLD_SIZE.get_airtable_client(
            self.conf.airtable, True
        )
        return delivery.Inventory(items)

    def on_status_update(self, record):
        if record.status == "Assigned / In Progress":
            delivery.on_assigned(
                record,
                member_table=self.member_table,
                inventory=self.inventory,
                sendgrid_client=self.sendgrid_client,
                settings=self.delivery_settings,
            )


ITEMS_BY_HOUSEHOLD_SIZE = airtable.TableSpec(
    name="items_by_household_size",
    model_cls=models.ItemsByHouseholdSizeModel,
)


TABLES = {
    "inbound": Inbound.table_spec,
    "members": Members.table_spec,
    "intake": Intake.table_spec,
    "items_by_household_size": ITEMS_BY_HOUSEHOLD_SIZE,
}
POLLABLE_TABLES = {
    "inbound": Inbound,
    "members": Members,
    "intake": Intake,
}
