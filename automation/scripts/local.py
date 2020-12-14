import argparse
import sys

from .. import tables
from ..utils import airtable


def main():
    parser = argparse.ArgumentParser(
        "A tool for running the automation locally"
    )
    parser.add_argument("action", choices=["poll"])
    parser.add_argument(
        "--table", type=lambda val: tables.Table[val.upper()], required=True
    )

    args = parser.parse_args()

    succeeded = True

    if args.action == "poll":
        succeeded = airtable.poll_table(args.table.value)
    else:
        raise ValueError("Unsupported action: {}".format(args.action))

    print("Succeeded!" if succeeded else "Failed!")
    sys.exit(0 if succeeded else 1)


if __name__ == "__main__":
    main()
