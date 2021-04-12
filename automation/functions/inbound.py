import structlog

log = structlog.get_logger("poll_inbound")


def on_new(record, inbound_table):
    UNKNOWN_CALLER_NUMBER = "696687"
    new_status = None
    last_record_updated_status = None

    if record.method == "Email":
        new_status = "Intake Needed"
    elif record.phone_number == UNKNOWN_CALLER_NUMBER:
        new_status = "Intake Needed"
    else:

        matching_records = inbound_table.get_all(
            formula=("{{Phone Number}} = {}".format(record.phone_number)),
            sort=[{"field": "createdTime", "direction": "desc"}],
            max_records=1,
        )
        last_record = matching_records[0] if matching_records else None

        if last_record is None:
            log.info("Did not find a previous record")
            new_status = "Intake Needed"
        else:
            last_record_to_new_record_status_map = {
                "Intake Needed": "Duplicate",
                "In Progress": "Duplicate",
                "Intake Complete": "Intake Needed",
                # ???
                "Duplicate": Exception(
                    'Should not have gotten a "duplicate" status'
                ),
                "Outside Bed-Stuy": "Intake Needed",
                "Call Back": "Duplicate",
                "Question/Info": "Intake Needed",
                "Thank you!": "Intake Needed",
                "Spanish-Intake needed": "Duplicate",
                "No longer needs assistance": "Intake Needed",
                "Phone Tag": "Duplicate",
                "Out of Service/Cannot Reach": "Duplicate",
            }
            last_record_updated_status_map = {
                "Phone Tag": "Call Back",
                "Out of Service/Cannot Reach": "Call Back",
            }

            if (
                last_record.status
                in last_record_to_new_record_status_map.keys()
            ):
                new_status = last_record_to_new_record_status_map[
                    last_record.status
                ]

            if last_record.status in last_record_updated_status_map.keys():
                last_record_updated_status = last_record_updated_status_map[
                    last_record.status
                ]

    # Check
    if new_status is None:
        raise Exception("")

    # Update the new record
    record.status = new_status

    # Update the last record
    if last_record_updated_status:
        last_record.status = last_record_updated_status

    if new_status == "Duplicate":
        last_record.other_inbounds = []
