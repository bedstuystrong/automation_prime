import enum

from . import models
from .functions import inbound, members
from .utils import airtable


class Table(enum.Enum):
    INBOUND = airtable.TableSpec(
        name="inbound",
        model_cls=models.InboundModel,
        status_to_cb={None: inbound.on_new},
    )
    MEMBERS = airtable.TableSpec(
        name="members",
        model_cls=models.MemberModel,
        status_to_cb={"New": members.on_new},
    )
