import flask
import twilio
from twilio.twiml.messaging_response import MessagingResponse

from utils import airtable, tables
from functions import inbound
from models import InboundModel


##########################
# GOOGLE CLOUD FUNCTIONS #
##########################


def poll_inbounds(event, context):
    print("event: {}".format(event))
    print("context: {}".format(context))

    poll_table(tables.Table.INBOUND)


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