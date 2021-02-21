import argparse
import contextlib
import json
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

from .. import config  # noqa: E402

##########
# CONSTS #
##########

RUNTIME = "python39"
SOURCE = str(Path(__file__).resolve().parents[2])

POLL_FUNCTION_NAMES = set(["poll_members"])
HTTP_FUNCTION_NAMES = set(["send_delivery_email"])

POLL_TOPIC_NAME = "POLL_TOPIC"
POLL_SCHEDULE = "* * * * *"
POLL_TRIGGER_JOB_NAME = "INBOUND_POLL_TRIGGER"
POLL_MESSAGE_BODY = "Trigger poll"


#########
# UTILS #
#########


@contextlib.contextmanager
def use_gcloud_project(project_id):
    config_get_proc = subprocess.run(
        ["gcloud", "config", "get-value", "project"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
    )

    original_project_id = config_get_proc.stdout.strip()
    if original_project_id == "":
        original_project_id = None

    try:
        subprocess.run(
            ["gcloud", "config", "set", "project", project_id],
            check=True,
        )
        yield
    finally:
        if original_project_id is not None:
            subprocess.run(
                ["gcloud", "config", "set", "project", original_project_id],
                check=True,
            )
        else:
            subprocess.run(
                ["gcloud", "config", "unset", "project"],
                check=True,
            )


############
# WRAPPERS #
############


def update():
    logging.info("Updating...")

    subprocess.run(["gcloud", "components", "update"], check=True)


def _list_names(gcloud_cmd):
    proc = subprocess.run(
        gcloud_cmd,
        stdout=subprocess.PIPE,
        check=True,
        encoding="utf-8",
    )

    entries = json.loads(proc.stdout)

    res = set()

    for entry in entries:
        res.add(entry["name"].split("/")[-1])

    return res


def list_topics():
    logging.info("Listing topics...")

    return _list_names(
        ["gcloud", "pubsub", "topics", "list", "--format", "json"],
    )


def list_scheduler_jobs():
    logging.info("Listing scheduler jobs...")

    return _list_names(
        ["gcloud", "scheduler", "jobs", "list", "--format", "json"],
    )


def list_functions():
    logging.info("Listing functions...")

    return _list_names(
        ["gcloud", "functions", "list", "--format", "json"],
    )


#############
# COMMMANDS #
#############


def deploy():
    logging.info("Deploying...")

    topics = list_topics()

    if POLL_TOPIC_NAME not in topics:
        logging.info("Creating topic: {}...".format(POLL_TOPIC_NAME))
        subprocess.run(
            ["gcloud", "pubsub", "topics", "create", POLL_TOPIC_NAME],
            check=True,
        )

    for func_name in POLL_FUNCTION_NAMES:
        logging.info("Creating poll function: {}...".format(func_name))
        subprocess.run(
            [
                "gcloud",
                "functions",
                "deploy",
                func_name,
                "--runtime",
                RUNTIME,
                "--trigger-topic",
                POLL_TOPIC_NAME,
                "--source",
                SOURCE,
            ],
            stdout=subprocess.DEVNULL,
            check=True,
        )

    jobs = list_scheduler_jobs()

    if POLL_TRIGGER_JOB_NAME not in jobs:
        logging.info("Creating scheduler job...")
        subprocess.run(
            [
                "gcloud",
                "scheduler",
                "jobs",
                "create",
                "pubsub",
                POLL_TRIGGER_JOB_NAME,
                "--topic",
                POLL_TOPIC_NAME,
                "--schedule",
                POLL_SCHEDULE,
                "--message-body",
                POLL_MESSAGE_BODY,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    for func_name in HTTP_FUNCTION_NAMES:
        logging.info("Creating http function: {}...".format(func_name))
        proc = subprocess.run(
            [
                "gcloud",
                "functions",
                "deploy",
                "--runtime",
                RUNTIME,
                "--trigger-http",
                "--allow-unauthenticated",
                "--format",
                "json",
                func_name,
            ],
            check=True,
            stdout=subprocess.PIPE,
        )

        url = json.loads(proc.stdout)["httpsTrigger"]["url"]
        logging.info("Trigger for {} is: {}".format(func_name, url))

    logging.info("Done.")


def reset():
    logging.info("Resetting...")

    topics = list_topics()

    if POLL_TOPIC_NAME in topics:
        logging.info("Deleting topic: {}...".format(POLL_TOPIC_NAME))
        subprocess.run(
            ["gcloud", "-q", "pubsub", "topics", "delete", POLL_TOPIC_NAME],
            check=True,
        )

    deployed_functions = list_functions() & (
        POLL_FUNCTION_NAMES | HTTP_FUNCTION_NAMES
    )

    for func_name in deployed_functions:
        logging.info("Deleting function: {}...".format(func_name))
        subprocess.run(
            [
                "gcloud",
                "-q",
                "functions",
                "delete",
                func_name,
            ],
            stdout=subprocess.DEVNULL,
        )

    jobs = list_scheduler_jobs()

    if POLL_TRIGGER_JOB_NAME in jobs:
        logging.info("Deleting scheduler job...")
        subprocess.run(
            [
                "gcloud",
                "-q",
                "scheduler",
                "jobs",
                "delete",
                POLL_TRIGGER_JOB_NAME,
            ],
            check=True,
        )


########
# MAIN #
########


def main():
    parser = argparse.ArgumentParser(
        description="Tool for setting up google cloud environment"
    )
    parser.add_argument("command", choices=["deploy", "reset"])

    args = parser.parse_args()

    google_cloud_config = config.load().google_cloud

    if google_cloud_config is None:
        parser.error(
            "Provided config path does not contain configuration for google "
            "cloud."
        )

    with use_gcloud_project(google_cloud_config.project_id):
        if args.command == "deploy":
            deploy()
        elif args.command == "reset":
            reset()
        else:
            assert False


if __name__ == "__main__":
    main()
