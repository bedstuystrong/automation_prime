from core import airtable, tables
from functions import inbound

#########
# UTILS #
#########

def poll_table(table, status_to_cb):
    client = airtable.Client()
    recs = client.poll(table)

    for record in client.poll(table):
        cb = status_to_cb.get(record.status)

        if cb is not None:
            cb(record)

##########################
# GOOGLE CLOUD FUNCTIONS #
##########################

def poll_inbounds(event, context):
    print("event: {}".format(event))
    print("context: {}".format(context))

    poll_table(tables.Table.INBOUND, {None: inbound.on_new})
