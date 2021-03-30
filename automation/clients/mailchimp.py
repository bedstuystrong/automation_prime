import hashlib
import mailchimp_marketing as MailchimpMarketing

from automation.config import MailchimpConfig

##########
# CLIENT #
##########


class MailchimpClient:
    def __init__(self, conf: MailchimpConfig):
        self._client = MailchimpMarketing.Client()
        self._client.set_config(
            {
                "api_key": conf.api_key,
                "server": conf.server_prefix,
            }
        )
        self._list_id = conf.list_id

    def _hash(self, email):
        string = email.lower().encode(encoding="utf-8")
        return hashlib.md5(string).hexdigest()

    def subscribe(self, email):
        member_info = {
            "email_address": email,
            "status": "subscribed",
            "status_if_new": "subscribed",
        }

        return self._client.lists.set_list_member(
            self._list_id, self._hash(email), member_info
        )
