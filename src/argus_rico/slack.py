__all__ = ["slack_app", "slack_app_starter"]

from typing import Any, Callable, Dict

from slack_bolt import App

from . import config, get_logger

log = get_logger("slack_bot")

slack_app = App(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET,
)


@slack_app.message("hi Rico")
def message_hello(message: Dict[str, Any], say: Callable[..., None]) -> None:
    # say() sends a message to the channel where the event was triggered
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
        None

    """
    # Acknowledge the action
    ack()
    if "telescope" in body["event"]["reaction"]:
        event = body["event"]
        thread_ts = event["item"]["ts"]
        say(
            f"<@{body['user']['id']}> initiated a follow-up request.",
            thread_ts=thread_ts,
        )


def slack_app_starter() -> None:
    log.info("Slack integration starting up...")
    slack_app.start(port=int(config.SLACK_PORT))
