import enum

from . import models
from .functions import inbound
from .utils import airtable


class Table(enum.Enum):
    INBOUND = airtable.TableSpec(
        name="inbound",
        model_cls=models.InboundModel,
        status_to_cb={None: inbound.on_new},
    )
