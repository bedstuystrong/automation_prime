# TODO : add a script that reads through all of the airtable data and validates
# it

import argparse
import sys
from collections import defaultdict

import pydantic

from .. import config, tables


def validate_table(table, conf):
    client = table.get_airtable_client(conf.airtable, read_only=True)

    validation_issues = defaultdict(list)

    # TODO: Don't reach inside our client wrapper, maybe move this to
    # AirtableClient?
    for page in client.client.get_iter():
        for raw in page:
            try:
                client.table_spec.model_cls.from_airtable(raw)
            except pydantic.error_wrappers.ValidationError as e:
                for issue in e.errors():
                    validation_issues[(issue["loc"], issue["type"])].append(
                        {"id": raw["id"], **raw["fields"]}
                    )

    if len(validation_issues) > 0:
        print(f"Validation Errors for '{table.name}' Table:")

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
    name_to_table = {t.name: t for t in tables.get_all_tables()}

    parser = argparse.ArgumentParser(
        "Validates all of the data in airtable with the models"
    )
    table_selection_group = parser.add_mutually_exclusive_group(required=True)
    table_selection_group.add_argument(
        "--table",
        choices=name_to_table.keys(),
    )
    table_selection_group.add_argument(
        "--all",
        action="store_true",
    )

    args = parser.parse_args()

    conf = config.load()

    provided_tables = None
    if args.table is not None:
        provided_tables = [name_to_table[args.table]]
    elif args.all is not None:
        provided_tables = list(name_to_table.values())

    assert provided_tables is not None

    succeeded = True
    for table in provided_tables:
        succeeded = validate_table(table, conf) and succeeded

    print("Succeeded." if succeeded else "Failed!")
    sys.exit(0 if succeeded else 1)


if __name__ == "__main__":
    main()
