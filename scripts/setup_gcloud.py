import argparse
import json
import subprocess
import logging

logging.basicConfig(level=logging.INFO)

from pathlib import Path

RUNTIME = "python38"
SOURCE = Path(__file__).resolve().parents[1]

FUNCTION_NAMES = {"poll_inbounds"}

POLL_TOPIC_NAME = "POLL_TOPIC"
POLL_SCHEDULE = "* * * * *"
POLL_TRIGGER_JOB_NAME = "INBOUND_POLL_TRIGGER"
POLL_MESSAGE_BODY = "Trigger poll"


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
            ["gcloud", "pubsub", "topics", "create", POLL_TOPIC_NAME], check=True
        )

    for func_name in FUNCTION_NAMES:
        logging.info("Creating function: {}...".format(func_name))
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

    logging.info("Done.")


def reset():
    logging.info("Resetting...")

    topics = list_topics()

    if POLL_TOPIC_NAME in topics:
        logging.info("Deleting topic: {}...".format(POLL_TOPIC_NAME))
        subprocess.run(
            ["gcloud", "-q", "pubsub", "topics", "delete", POLL_TOPIC_NAME], check=True
        )

    deployed_functions = list_functions() & FUNCTION_NAMES

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

    update()

    if args.command == "deploy":
        deploy()
    elif args.command == "reset":
        reset()
    else:
        assert False


if __name__ == "__main__":
    main()
