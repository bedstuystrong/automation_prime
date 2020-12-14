def on_new(record):
    record.status = "Processed"

    return record
