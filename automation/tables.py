from . import models
from .functions import administrative, inbound, members
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

INTAKE_TICKETS = airtable.TableSpec(
    name="intake_tickets",
    model_cls=models.IntakeTicketModel,
    status_to_cb=dict(),
)

ADMINISTRATIVE = airtable.TableSpec(
    name="administrative",
    model_cls=models.AdministrativeModel,
    status_to_cb={"Update Needed": administrative.UpdateNeededCallback},
)


# TODO : find a better way to do this that won't get out of date
def get_all_tables():
    return [INBOUND, MEMBERS, INTAKE_TICKETS, ADMINISTRATIVE]
