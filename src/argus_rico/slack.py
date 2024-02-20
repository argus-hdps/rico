__all__ = ["SlackRico"]

import slack_sdk as sk

from . import config


class SlackRico:
    def __init__(self):
        self.sc = sk.WebClient(token=config.SLACK_BOT_TOKEN)
        self.bot_id = self.sc.api_call("auth.test")["user_id"]

    def on_slack_say(self, channel, message):
        try:
            response = self.sc.chat_postMessage(
                channel=channel,
                text=message,
            )
        except sk.errors.SlackApiError as e:
            # assert e.response["error"]
            try:
                return e.response["ok"]
            except KeyError:
                return None
        return response["ok"]

    def post_file_to_slack(self, channel, title, message, file):
        try:
            response = self.sc.files_upload(
                channels=channel,  # You can specify multiple channels here in the form of a string array
                title=title,
                file=file,
                initial_comment=message,
            )

        except sk.errors.SlackApiError as e:
            # assert e.response["error"]
            try:
                return e.response["ok"]
            except KeyError:
                return None
        return response["ok"]
