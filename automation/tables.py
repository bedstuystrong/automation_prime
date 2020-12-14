import enum

from . import models
from .functions import inbound, volunteers
from .utils import airtable


class Table(enum.Enum):
    INBOUND = airtable.TableSpec(
        name="inbound",
        model_cls=models.InboundModel,
        status_to_cb={None: inbound.on_new},
    )
    VOLUNTEERS = airtable.TableSpec(
        name="volunteers",
        model_cls=models.VolunteerModel,
        status_to_cb={"New": volunteers.on_new},
    )
