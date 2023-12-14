__all__ = ["slack_app", "slack_app_starter"]
import datetime
import os
import time
from typing import Any, Callable, Dict

import slack_sdk as sk
from sanitize_filename import sanitize
from slack_bolt import App

from . import config, get_logger
from . import images as rimages
from .efte.efte_runner import EFTERunner

log = get_logger("slack_bot")

if config.SLACK_BOT_TOKEN is not None:
    slack_app = App(
        token=config.SLACK_BOT_TOKEN,
        signing_secret=config.SLACK_SIGNING_SECRET,
    )


@slack_app.event("message")
def handle_message_events(body: Dict[str, Any]) -> None:
    """Handle message events in the Slack app.

    Args:
        body (Dict[str, Any]): The payload containing the event data.

    Returns:
        None.
    """
    pass


@slack_app.message("hi Rico")
def message_hello(message: Dict[str, Any], say: Callable[..., None]) -> None:
    """Handle the "hi Rico" message event in the Slack app.

    Args:
        message (Dict[str, Any]): The incoming message data.
        say (Callable[..., None]): Function to send a message as a response.

    Returns:
        None.
    """
    say(f"Hey there <@{message['user']}>!", thread_ts=message["ts"])


@slack_app.event("reaction_added")
def telescope_trigger(
    body: Dict[str, Any], ack: Callable[..., None], say: Callable[..., None]
) -> None:
    """
    Triggered when a reaction is added in the Slack app.

    Args:
        body (dict): The payload containing the event data.
        ack (function): Acknowledgment function to confirm the event was received.
        say (function): Function to send a message as a response.

    Returns:
        None.
    """
    # Acknowledge the action
    ack()
    if "telescope" in body["event"]["reaction"]:
        event = body["event"]
        thread_ts = event["item"]["ts"]
        say(
            f"<@{event['user']}> initiated a follow-up request.",
            thread_ts=thread_ts,
        )


@slack_app.shortcut("rico_lightcurve_req")
def open_lcv_modal(ack, shortcut, client):
    """Open a modal for requesting a lightcurve in the Slack app.

    Args:
        ack (Callable[..., None]): Acknowledgment function to confirm the shortcut request.
        shortcut (Dict[str, Any]): The shortcut data.
        client: The Slack WebClient instance.

    Returns:
        None.
    """
    # Acknowledge the shortcut request
    ack()
    # Call the views_open method using the built-in WebClient
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        # A simple view payload for a modal
        view={
            "type": "modal",
            "callback_id": "modal-lcv-req",
            "title": {"type": "plain_text", "text": "Forced Photometry", "emoji": True},
            "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
            "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "target_name",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "title",
                        "placeholder": {"type": "plain_text", "text": "TRAPPIST-1"},
                    },
                    "label": {"type": "plain_text", "text": "Target Name"},
                },
                {
                    "type": "actions",
                    "block_id": "time_range",
                    "elements": [
                        {
                            "type": "datepicker",
                            "initial_date": "2015-07-01",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select a date",
                                "emoji": True,
                            },
                            "action_id": "start_date",
                        },
                        {
                            "type": "datepicker",
                            "initial_date": "2030-01-01",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select a date",
                                "emoji": True,
                            },
                            "action_id": "end_date",
                        },
                    ],
                },
                {
                    "type": "input",
                    "block_id": "right_ascension",
                    "element": {
                        "type": "number_input",
                        "is_decimal_allowed": True,
                        "action_id": "number_input-action",
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Right Ascension",
                        "emoji": True,
                    },
                },
                {
                    "type": "input",
                    "block_id": "declination",
                    "element": {
                        "type": "number_input",
                        "is_decimal_allowed": True,
                        "action_id": "number_input-action",
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Declination",
                        "emoji": True,
                    },
                },
            ],
        },
    )


@slack_app.view("modal-lcv-req")
def handle_submission(
    ack: Callable[..., None], body: Dict[str, Any], client: sk.WebClient
) -> None:
    """Handle the submission of the lightcurve request modal in the Slack app.

    Args:
        ack (Callable[..., None]): Acknowledgment function to confirm the submission.
        body (Dict[str, Any]): The payload containing the submission data.
        client: The Slack WebClient instance.

    Returns:
        None.
    """
    values = body["view"]["state"]["values"]
    user = body["user"]["id"]

    print(values)

    target_name = sanitize(values["target_name"]["title"]["value"])
    start_date = values["time_range"]["start_date"]["selected_date"]
    end_date = values["time_range"]["end_date"]["selected_date"]
    right_ascension = float(values["right_ascension"]["number_input-action"]["value"])
    declination = float(values["declination"]["number_input-action"]["value"])

    errors = {}
    if (right_ascension < 0) or (right_ascension > 360):
        errors["right_ascension"] = "Right ascension out of range."
    if (declination < -90) or (declination > 90):
        errors["declination"] = "Declination out of range."
    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return
    # Acknowledge the view_submission request and close the modal
    ack()
    # Do whatever you want with the input data - here we're querying the DB and
    # then passing off the lcv gen to a background worker

    # TODO: probably can refactor this to only hit the DB once, but what's 15
    # seconds out of 5 hours?
    nimages = len(
        rimages.images_containing(
            right_ascension,
            declination,
            datetime.datetime.strptime(start_date, "%Y-%m-%d"),
            datetime.datetime.strptime(end_date, "%Y-%m-%d"),
        )
    )
    uncompleteable = False
    # Message to send user
    msg = ""
    try:
        if nimages >= 1:
            msg = f"Hi <@{user}>! I have received your request to produce the following lightcurve:\n*{target_name}* at RA: {right_ascension}, Dec: {declination}.\nFrom {start_date} to {end_date}.\n\n *Please note that I don't know how long this will take! Your table will be uploaded here ASAP.*"
        else:
            msg = f"Hi <@{user}>! I received your forced photometry request, but didn't find any images."
            uncompleteable = True
    except Exception as e:
        # Handle error
        msg = f"There was an error with your submission: {e}"
    #
    # Message the user
    try:
        response = client.chat_postMessage(channel=user, text=msg)
    except Exception as e:
        print(f"Failed to post a message {e}")
        return
    if uncompleteable:
        return

    dm_channel = response["channel"]
    print(
        f"efte -n 72 autophot --mindate {start_date} --maxdate {end_date} -o {target_name} {right_ascension} -- {declination}"
    )

    er = EFTERunner()
    er.run(
        f"efte -n 72 autophot --mindate {start_date} --maxdate {end_date} -o {target_name} {right_ascension} -- {declination}"
    )
    output = (
        target_name
        + f"_{right_ascension:.2f}_{declination:.2f}".replace(".", "d").replace(
            "-", "m"
        )
        + ".fits"
    )
    while not os.path.isfile(output):
        time.sleep(60)

    client.files_upload_v2(
        file=f"./{output}",
        channel=dm_channel,
        title=output,
        initial_comment="Your lightcurve is ready!",
    )


def slack_app_starter() -> None:
    log.info("Slack integration starting up...")
    slack_app.start(port=int(config.SLACK_PORT))


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
