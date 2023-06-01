import sys
from typing import Sequence

import click


@click.group()
def main() -> None:
    """Console scripts for rico."""
    pass


class Config(object):
    """Contains global options used for all pipeline actions."""

    def __init__(self) -> None:
        self.verbose = False
        self.ncpus = 1


pass_config = click.make_pass_decorator(Config, ensure=True)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover


@click.command("slack", short_help="Start Rico Slack server.")
def slack() -> None:
    """Starts the Rico Slack server."""
    from .slack import slack_app_starter

    slack_app_starter()


@click.command("index_images", short_help="Index EVR images directly into MongoDB.")
@click.argument("directories", nargs=-1, type=click.Path(exists=True))
@pass_config
def index_images(cli_config: Config, directories: Sequence[str]) -> None:
    """Indexes EVR images from the specified directories.

    Args:
        cli_config: Config object containing global options.
        directories: Iterable of directories containing EVR images.

    """
    import multiprocessing as mp

    from . import EVRImageLoader

    image_loader = EVRImageLoader(create_client=False)

    pool = mp.Pool(cli_config.ncpus)

    directories = sorted(directories)
    n_directories = len(directories)
    out = []
    with click.progressbar(
        pool.imap_unordered(image_loader.load_directory, directories),
        label="Loading: ",
        length=n_directories,
    ) as pbar:
        for _ in pbar:
            out.append(_)

    pool.close()
    pool.join()


main.add_command(slack)
main.add_command(index_images)
