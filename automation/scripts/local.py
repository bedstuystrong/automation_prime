import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO)

from .. import config, tables  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        "A tool for running the automation locally"
    )
    parser.add_argument("action", choices=["poll"])
    parser.add_argument(
        "--table",
        type=lambda val: getattr(tables, val.upper()),
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
    client = args.table.get_airtable_client(
        conf.airtable, read_only=not args.live
    )

    succeeded = True
    if args.action == "poll":
        succeeded = client.poll_table(conf)
    else:
        raise ValueError("Unsupported action: {}".format(args.action))

    print("Succeeded!" if succeeded else "Failed!")
    sys.exit(0 if succeeded else 1)


if __name__ == "__main__":
    main()
