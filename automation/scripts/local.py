import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO)

from .. import config, tables  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        "A tool for running the automation locally"
    )
    parser.add_argument("action", choices=["poll", "migrate-meta"])
    parser.add_argument(
        "--table",
        required=True,
        help="Which Airtable table to use",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enables updating airtable records",
    )

    args = parser.parse_args()

    conf = config.load()
    table = tables.POLLABLE_TABLES[args.table](conf, read_only=not args.live)

    succeeded = True
    if args.action == "poll":
        succeeded = table.poll_table()
    elif args.action == "migrate-meta":
        client = table.get_airtable(conf.airtable, read_only=not args.live)
        # TODO: once airtable-python-wrapper releases a version with batched
        # updates, make this use a paginated query and batched updates
        for record in client.get_all_with_new_status():
            if (
                record.meta_last_seen_status is None
                and record.meta is not None
            ):
                last_seen_status = record.meta["lastSeenStatus"]
                logging.info(
                    f"Updating {record.id} to have last seen status "
                    f"{last_seen_status}"
                )
                client.client.update(
                    record.id, {"_meta_last_seen_status": last_seen_status}
                )
    else:
        raise ValueError("Unsupported action: {}".format(args.action))

    print("Succeeded!" if succeeded else "Failed!")
    sys.exit(0 if succeeded else 1)


if __name__ == "__main__":
    main()
