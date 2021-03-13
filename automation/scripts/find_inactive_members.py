import argparse
from collections import defaultdict
import datetime
import json
import sys
from pathlib import Path

from automation import config
from automation.clients import slack
from automation.tables import Intake, Members

CUTOFF_DATE = datetime.datetime.now(
    datetime.timezone.utc
) - datetime.timedelta(days=7 * 4 * 4)


def main():
    parser = argparse.ArgumentParser(
        description="Finds inactive members, and dumps them to a file"
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output file to dump inactive member IDs to",
    )
    args = parser.parse_args()

    # NOTE make sure the file exists before we embark on our quest
    args.out.touch()

    print("Warning: this script can take up to an hour to run...")

    conf = config.load()

    slack_client = slack.SlackClient(conf.slack)

    members_client = Members.get_airtable(conf.airtable)
    intake_client = Intake.get_airtable(conf.airtable)

    print("Getting members...")

    members = list(members_client.get_all())
    print(f"Found {len(members)} member records")

    slack_id_to_member = dict()
    num_duplicates = 0

    for m in members:
        if m.slack_user_id is not None:
            if m.slack_user_id in slack_id_to_member:
                num_duplicates += 1

            slack_id_to_member[m.slack_user_id] = m

    print(
        f"Found {len(slack_id_to_member)} unique slack IDs, with "
        f"{num_duplicates} duplicates"
    )

    def member_particpated(m):
        for ticket_id in [
            *reversed(m.delivery_tickets),
            *reversed(m.intake_tickets),
        ]:
            ticket = intake_client.get(ticket_id)

            if (
                ticket.date_completed is not None
                and datetime.datetime(
                    year=ticket.date_completed.year,
                    month=ticket.date_completed.month,
                    day=ticket.date_completed.day,
                    tzinfo=datetime.timezone.utc,
                )
                >= CUTOFF_DATE
            ):
                return True

        return False

    print("Determining which members have done intake or delivery...")
    member_id_to_particpated = {m.id: member_particpated(m) for m in members}
    num_particpated = sum(
        1 for particpated in member_id_to_particpated.values() if particpated
    )

    print(f"Found {num_particpated} members who participated")

    user_to_latest_login_date = dict()

    print("Getting Slack access logs...")

    for log in slack_client.team.access_logs(after=CUTOFF_DATE):
        cur_latest_login_date = user_to_latest_login_date.get(log.user_id)

        if (
            cur_latest_login_date is None
            or cur_latest_login_date < log.date_last
        ):
            user_to_latest_login_date[log.user_id] = log.date_last

    print(f"Found logins for {len(user_to_latest_login_date)} users")

    active_reason_to_count = defaultdict(int)
    inactive_members = list()
    for m in members:
        if member_id_to_particpated[m.id]:
            active_reason_to_count["particpated"] += 1
            continue

        if m.created_at > CUTOFF_DATE:
            active_reason_to_count["new"] += 1
            continue

        if m.slack_user_id is not None:
            last_login = user_to_latest_login_date.get(m.slack_user_id)
            if last_login is not None and last_login >= CUTOFF_DATE:
                active_reason_to_count["login"] += 1
                continue

        inactive_members.append(m)

    print(
        "Found {} inactive members: {}".format(
            len(inactive_members),
            ", ".join(
                f"{reason}: {count}"
                for (reason, count) in active_reason_to_count.items()
            ),
        )
    )

    print(f"Dumping inactive members ids to: {args.out}...")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump([m.id for m in inactive_members], f)

    return 0


if __name__ == "__main__":
    sys.exit(main())
