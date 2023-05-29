"""Console scripts for rico."""
import sys

import click


@click.group()
def main() -> None:
    pass


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover


@click.command("say_goodnight", short_help="Say goodnight.")
@click.argument("please", type=str)
@click.option(
    "--gracie",
    "-g",
    type=str,
    default="Gracie",
    help="Gracie!",
)
def say_goodnight(please: str, gracie: str) -> None:
    click.echo(f"Goodnight, {gracie}!")


@click.command("slack", short_help="Start Rico Slack server.")
def slack() -> None:
    from .slack import slack_app_starter

    slack_app_starter()


main.add_command(say_goodnight)
main.add_command(slack)
