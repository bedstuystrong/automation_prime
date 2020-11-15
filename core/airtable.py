from airtable import Airtable

from core import config


class Client:
    def __init__(self):
        self._table_to_client = {}

    def _get_client(self, table):
        if table not in self._table_to_client.keys():
            self._table_to_client[table] = Airtable(
                config.Config.load().airtable.base_id,
                table.value.get_airtable_name(),
                config.Config.load().airtable.api_key,
            )

        return self._table_to_client[table]

    def get_all(self, table, formula=None):
        return [
            table.value.model_cls.from_airtable(raw)
            for raw in self._get_client(table).get_all(formula=formula)
        ]

    def poll(self, table):
        # TODO : sort by creation time asc
        return [
            table.value.model_cls.from_airtable(raw)
            for raw in self._get_client(table).get_all(
                formula=(
                    "OR({Status} != {_meta_last_seen_status}, "
                    "AND({Status} = BLANK(), {_meta_last_seen_status} = BLANK()))"
                )
            )
        ]