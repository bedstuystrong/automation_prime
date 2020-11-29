# TODO : add a script that reads through all of the airtable data and validates it

import sys
from collections import defaultdict
from pathlib import Path

import pydantic

from .. import models, tables
from ..utils import airtable


def main():
    client = airtable.Client()

    validation_errors = defaultdict(int)

    PAGE_MOD = 500
    for table in list(tables.Table):
        i = 0
        for page in client._get_client(table.value).get_iter():
            for raw in page:
                try:
                    rec = table.value.model_cls.from_airtable(raw)

                    if i % PAGE_MOD == 0:
                        print("Processed {} records...".format(i))

                    i += 1
                except pydantic.error_wrappers.ValidationError as e:
                    for val in e.errors():
                        assert val.keys() == {"loc", "msg", "type"}
                        validation_errors[(val["loc"], val["msg"], val["type"])] += 1
                except StopIteration:
                    break

    had_errors = False

    if len(validation_errors) > 0:
        had_errors = True

        print("Validation Errors:")

        for (loc, msg, t), num in sorted(
            validation_errors.items(), key=lambda tup: tup[1]
        ):
            print(
                "\t- Encountered {} validation errors: loc={}, msg={}, type={}".format(
                    num, loc, msg, t
                )
            )

    if not had_errors:
        print("All Good!")
        sys.exit(0)
    else:
        print("Failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
