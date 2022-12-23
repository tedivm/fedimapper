import asyncio
import sqlite3
import sys
from functools import wraps

import typer
from ruamel.yaml import YAML
from tld.utils import update_tld_names

from .run import get_next_instance
from .services import mastodon
from .settings import settings
from .tasks import ingest
from .tasks.ingest import ingest_host
from .utils.queuerunner import QueueRunner
from .utils.queuerunner import Settings as QueueSettings

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
app = typer.Typer()


def pretty_print(data):
    yaml.dump(data, sys.stdout)


def syncify(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@app.command()
def instance(host: str):
    pretty_print(mastodon.get_metadata(host))


@app.command()
def instance_version(host: str):
    metadata = mastodon.get_metadata(host)
    if not metadata:
        typer.echo("Unable to get metdata.")
        sys.exit(1)

    if not "version" in metadata:
        typer.echo("Unable to get version string.")
        sys.exit(1)

    pretty_print(dict(mastodon.get_version_breakdown(metadata["version"])))


@app.command()
def instance_peers(host: str):
    pretty_print(mastodon.get_peers(host))


@app.command()
def instance_blocks(host: str):
    pretty_print(mastodon.get_blocked_instances(host))


@app.command()
def instance_blocks(host: str):
    pretty_print(mastodon.get_blocked_instances(host))


@app.command()
@syncify
async def ingest_instance(host: str):
    await ingest.ingest_host(host)
    typer.echo("Ingest complete.")


@app.command()
@syncify
async def crawl(
    num_processes: int = typer.Option(None, help="Last name of person to greet."),
):
    typer.echo("Update TLD database.")
    update_tld_names()
    typer.echo("Run queue processing.")

    queue_settings = QueueSettings(num_processes=num_processes, lookup_block_size=num_processes * 4)

    runner = QueueRunner("ingest", reader=ingest_host, writer=get_next_instance, settings=queue_settings)
    await runner.main()


@app.command()
def vacuum_database():
    sqlite_prefix = "sqlite:///"
    if not settings.database_url.startswith(sqlite_prefix):
        typer.echo("Vacuum only works with sqlite databases.")
        sys.exit(1)

    db_file = settings.database_url.replace(sqlite_prefix, "")
    conn = sqlite3.connect(db_file, isolation_level=None)
    conn.execute("VACUUM")
    conn.close()


if __name__ == "__main__":
    app()
