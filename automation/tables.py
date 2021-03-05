import abc
from functools import cached_property

import sendgrid

from . import config, models
from .functions import delivery, inbound, members
from .clients import airtable, slack


class PollableTable(abc.ABC):

    table_spec = ...

    def __init__(self, conf: config.Config, read_only=False):
        self.conf = conf
        self.read_only = read_only

    @classmethod
    def get_airtable(cls, conf: config.AirtableConfig, read_only=False):
        return cls.table_spec.get_airtable_client(conf, read_only=read_only)

    def poll_table(self):
        client = self.get_airtable(self.conf.airtable, self.read_only)
        return client.poll_table(self.on_status_update)

    @abc.abstractmethod
    def on_status_update(self, record):
        ...


class SlackMixin:
    @cached_property
    def slack_client(self):
        return slack.SlackClient(self.conf.slack)


class EmailMixin:
    @cached_property
    def sendgrid_client(self):
        return sendgrid.SendGridAPIClient(self.conf.sendgrid.api_key)

    @property
    def from_email(self):
        return self.conf.sendgrid.from_email

    @property
    def reply_to(self):
        return self.conf.sendgrid.reply_to


class Inbound(PollableTable):

    table_spec = airtable.TableSpec(
        name="inbound",
        model_cls=models.InboundModel,
    )

    def on_status_update(self, record):
        inbound.on_new(record)


class Members(PollableTable, SlackMixin, EmailMixin):

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
                from_email=self.from_email,
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
                from_email=self.from_email,
                reply_to=self.reply_to,
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
