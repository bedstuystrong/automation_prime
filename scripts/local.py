import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))

from automation import config, models
from automation.utils import airtable


def main():
    parser = argparse.ArgumentParser("A tool for running the automation locally")
    parser.add_argument("action", choices=["poll"])
    parser.add_argument("--table", type=lambda val: config.Table[val.upper()], required=True)

    args = parser.parse_args()

    if args.action == "poll":
        airtable.poll_table(args.table.value)
    else:
        raise ValueError("Unsupported action: {}".format(args.action))

    sys.exit(0)


if __name__ == "__main__":
    main()