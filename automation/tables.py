from . import models
from .functions import inbound, members
from .clients import airtable

INBOUND = airtable.TableSpec(
    name="inbound",
    model_cls=models.InboundModel,
    status_to_cb={None: inbound.NewCallback},
)

MEMBERS = airtable.TableSpec(
    name="members",
    model_cls=models.MemberModel,
    status_to_cb={"New": members.NewCallback},
)

INTAKE = airtable.TableSpec(
    name="intake",
    model_cls=models.IntakeModel,
    status_to_cb={},
)
