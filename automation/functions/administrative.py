import logging


from automation import config, tables
from automation.models import AdministrativeModel

logger = logging.getLogger(__name__)


class UpdateNeededCallback:
    def __init__(self, conf: config.Config):
        self._conf = conf

    def _update_delivery_backlog_unassigned(self, administrative_model):
        client = tables.INTAKE_TICKETS.get_airtable_client(
            self._conf.airtable, read_only=True
        )
        administrative_model.value = sum(
            1 if ticket_model.status == "Seeking Volunteer" else 0
            for ticket_model in client.get_all()
        )

        return administrative_model

    def _update_delivery_backlog_in_progress(self, administrative_model):
        client = tables.INTAKE_TICKETS.get_airtable_client(
            self._conf.airtable, read_only=True
        )
        administrative_model.value = sum(
            1 if ticket_model.status == "Assigned / In Progress" else 0
            for ticket_model in client.get_all()
        )

        return administrative_model

    def _update_inbound_backlog(self, administrative_model):
        client = tables.INBOUND.get_airtable_client(
            self._conf.airtable, read_only=True
        )
        administrative_model.value = sum(
            (
                1
                if inbound_model.status
                in inbound_model.get_nonterminal_statuses()
                else 0
            )
            for inbound_model in client.get_all()
        )

        return administrative_model

    def __call__(self, administrative_model):
        # TODO : clean this up
        name_to_updater = {}
        name_to_updater[
            AdministrativeModel.Names.DELIVERY_BACKLOG_UNASSIGNED
        ] = self._update_delivery_backlog_unassigned
        name_to_updater[
            AdministrativeModel.Names.DELIVERY_BACKLOG_IN_PROGRESS
        ] = self._update_delivery_backlog_in_progress
        name_to_updater[
            AdministrativeModel.Names.INBOUND_BACKLOG
        ] = self._update_inbound_backlog

        updater = name_to_updater.get(administrative_model.name)

        if updater is not None:
            logger.info(
                "Updating administrative value for: {}".format(
                    administrative_model.name.value
                )
            )

            updater(administrative_model)
        else:
            logger.info(
                f"No updater registered for: {administrative_model.name.value}"
            )

        administrative_model.status = "Updated"

        return administrative_model
