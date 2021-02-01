import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO)

from .. import tables  # noqa: E402
from ..utils import airtable  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        "A tool for running the automation locally"
    )
    parser.add_argument("action", choices=["poll"])
    parser.add_argument(
        "--table",
        type=lambda val: tables.Table[val.upper()],
        required=True,
        help="Which Airtable table to use",
    )
    parser.add_argument(
        "--live",
        type=bool,
        default=False,
        help="Enables updating airtable records",
    )

    args = parser.parse_args()

    client = airtable.AirtableClient(read_only=not args.live)

    succeeded = True
    if args.action == "poll":
        succeeded = airtable.poll_table(client, args.table.value)
    else:
        raise ValueError("Unsupported action: {}".format(args.action))

    print("Succeeded!" if succeeded else "Failed!")
    sys.exit(0 if succeeded else 1)


if __name__ == "__main__":
    main()
