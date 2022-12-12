import asyncio
import sys
from functools import wraps

import typer
from ruamel.yaml import YAML

from .services import mastodon
from .tasks import ingest

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


if __name__ == "__main__":
    app()
