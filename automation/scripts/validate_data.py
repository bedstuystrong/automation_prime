# TODO : add a script that reads through all of the airtable data and validates
# it

import argparse
import sys
from collections import defaultdict

import pydantic

from .. import tables
from ..utils import airtable


def validate_table(client, table):
    validation_issues = defaultdict(list)

    for page in client._get_client(table).get_iter():
        for raw in page:
            try:
                table.model_cls.from_airtable(raw)
            except pydantic.error_wrappers.ValidationError as e:
                for issue in e.errors():
                    validation_issues[(issue["loc"], issue["type"])].append(
                        {"id": raw["id"], **raw["fields"]}
                    )

    if len(validation_issues) > 0:
        print("Found the following validation errors:")

        for (
            validation_error_loc,
            validation_error_type,
        ), failed_raw_records in validation_issues.items():
            print(
                "- {} ({}):".format(
                    ", ".join(validation_error_loc), validation_error_type
                )
            )

            for raw in failed_raw_records:
                print(
                    "   + {}: {}".format(
                        raw["id"],
                        ", ".join(
                            f"{loc}={repr(raw.get(loc))}"
                            for loc in validation_error_loc
                        ),
                    )
                )

        return False
    else:
        return True


def main():
    parser = argparse.ArgumentParser(
        "Validates all of the data in airtable with the models"
    )
    parser.add_argument(
        "--table",
        choices=[t.name.lower() for t in tables.Table],
        required=True,
    )

    args = parser.parse_args()

    client = airtable.AirtableClient()

    succeeded = validate_table(client, tables.Table[args.table.upper()].value)

    print("Succeeded." if succeeded else "Failed!")
    sys.exit(0 if succeeded else 1)


if __name__ == "__main__":
    main()
