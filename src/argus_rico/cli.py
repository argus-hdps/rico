import sys
from typing import Sequence

import click


class Config(object):
    """Contains global options used for all pipeline actions."""

    def __init__(self) -> None:
        self.verbose = False
        self.ncpus = 36


pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option(
    "--ncpus", "-n", nargs=1, default=36, type=int, help="Number of spawned processes."
)
@pass_config
def main(config, ncpus) -> None:
    """Console scripts for rico."""
    config.ncpus = ncpus


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover


@click.command("slack", short_help="Start Rico Slack server.")
def slack() -> None:
    """Starts the Rico Slack server."""
    from .slack_app import slack_app_starter

    slack_app_starter()


@click.command("loadcats", short_help="Start Rico monitor for EFTE catalogs.")
@click.argument("directory", type=click.Path(exists=True))
def loadcats(directory: str) -> None:
    """Starts the Rico directory monitor."""
    from .efte.watchdog import EFTEWatcher

    ew = EFTEWatcher(watch_path=directory)
    ew.watch()


@click.command("stream_json", short_help="Record event stream to local JSON.")
@click.option(
    "--filter",
    "-f",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="File containing filters to apply to alert stream",
)
@click.option(
    "--outdir",
    "-o",
    type=click.Path(file_okay=False),
    default="rico_alerts",
    help="Output directory",
)
@click.option("--group", "-g", type=str, default="argus-spec", help="Kafka group ID")
def stream_json(filter: str, outdir: str, group: str) -> None:
    """Monitor the alert stream and record candidates to local disk in JSON
    format. Optionally, apply a filter to the events before recording, based on
    xmatch info."""
    import os

    from .efte.stream import EFTEAlertReceiver

    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    ear = EFTEAlertReceiver(
        output_path=outdir,
        filter_path=filter,
        group=group,
    )
    ear.poll_and_record()


@click.command(
    "index_images", short_help="Index EVR images directly, to file or to MongoDB."
)
@click.argument("directories", nargs=-1, type=click.Path(exists=True))
@click.option("--db_index", "-d", is_flag=True, default=False, help="MongoDB index")
@click.option("--file", "-f", is_flag=True, default=False, help="JSON index")
@click.option(
    "--summarize", "-s", is_flag=True, default=False, help="Summarize from glob pattern"
)
@pass_config
def index_images(
    cli_config: Config,
    directories: Sequence[str],
    db_index: bool,
    file: bool,
    summarize: bool,
) -> None:
    """Indexes EVR images from the specified directories. With the `--db`
    option, we index into MongoDB. With the `--file` option, the index is
    exclusively a standalone JSON.


    Finally, with `--summarize`, we can combine many JSON manifests into a
    flattened Parquet-format table.


    Args:
        cli_config: Config object containing global options.
        directories: Iterable of directories containing EVR images.

    """
    import multiprocessing as mp

    from .efte import EVRNightSerializer

    if file:
        image_loader = EVRNightSerializer()
    elif db_index:
        from .efte import EVRImageLoader

        image_loader = EVRImageLoader(create_client=False)

    if file or db_index:
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

    if summarize:
        dirnames = [dirname[:-1] if dirname[-1] == "/"  else dirname for dirname in directories]
        jsons = [dirname + ".json" for dirname in dirnames]

        out_df = EVRNightSerializer.summarize(jsons)
        out_df.to_parquet("summary.parquet")


@click.command("gn", short_help="Say goodnight, Gracie!.")
@pass_config
def gn(cli_config: Config) -> None:
    print("Goodnight, Gracie!")
    print(cli_config.ncpus)


main.add_command(slack)
main.add_command(index_images)
main.add_command(loadcats)
main.add_command(stream_json)
main.add_command(gn)
