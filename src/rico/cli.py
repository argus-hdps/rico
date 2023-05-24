"""Console scripts for rico."""
import sys

import click


@click.group()
def main():
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
def say_goodnight(please, gracie):
    click.echo(f"Goodnight, {gracie}!")


main.add_command(say_goodnight)
