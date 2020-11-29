import flask
import twilio
from twilio.twiml.messaging_response import MessagingResponse

from automation import tables
from automation.models import InboundModel
from automation.utils import airtable


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################


def poll_inbounds(event, context):
    airtable.poll_table(tables.Table.INBOUND.value)


def handle_inbound_message(request):
    request_json = request.get_json(silent=True)
    request_args = request.args

    print(request_json)
    print(request_args)

    model = InboundModel(
        method="Text Message",
        phone_number=request_json["From"],
        message=request_json["Body"],
    )

    print(model)

    return str(MessagingResponse())
