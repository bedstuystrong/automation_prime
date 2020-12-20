from ..utils import slack


def on_new(volunteer_model):
    slack_client = slack.SlackClient()

    volunteer_model.status = "Processed"

    slack_user = slack_client.users_lookupByEmail(volunteer_model.email)

    if slack_user is not None:
        volunteer_model.slack_handle = slack_user.get_handle()
        volunteer_model.slack_email = slack_user.profile.email
        volunteer_model.slack_user_id = slack_user.id
