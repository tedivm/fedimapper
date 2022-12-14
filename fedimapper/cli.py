import asyncio
import json
import sqlite3
import sys
from functools import wraps

import typer
from fastapi.encoders import jsonable_encoder
from ruamel.yaml import YAML
from tld.utils import update_tld_names

from fedimapper.run import get_next_instance
from fedimapper.services import mastodon, nodeinfo, www
from fedimapper.settings import settings
from fedimapper.tasks import ingest
from fedimapper.tasks.ingest import ingest_host
from fedimapper.utils.queuerunner import QueueRunner
from fedimapper.utils.queuerunner import Settings as QueueSettings

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
app = typer.Typer()


def pretty_print(data):
    yaml.dump(jsonable_encoder(data), sys.stdout)


def syncify(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@app.command()
def generate_openapi_spec():
    from fedimapper.www import app

    print(json.dumps(app.openapi(), indent=2))


@app.command()
@syncify
async def instance_nodeinfo(host: str):
    pretty_print(await nodeinfo.get_nodeinfo(www.get_node_actual_host(host)))


@app.command()
def instance(host: str):
    pretty_print(mastodon.get_metadata(www.get_node_actual_host(host)))


@app.command()
def instance_version(host: str):
    metadata = mastodon.get_metadata(www.get_node_actual_host(host))
    if not metadata:
        typer.echo("Unable to get metadata.")
        sys.exit(1)

    if not "version" in metadata:
        typer.echo("Unable to get version string.")
        sys.exit(1)

    pretty_print(dict(mastodon.get_version_breakdown(metadata["version"])))


@app.command()
def instance_peers(host: str):
    pretty_print(mastodon.get_peers(www.get_node_actual_host(host)))


@app.command()
def instance_blocks(host: str):
    pretty_print(mastodon.get_blocked_instances(www.get_node_actual_host(host)))


@app.command()
@syncify
async def ingest_instance(host: str):
    from fedimapper.services import db_session

    async with db_session.get_session() as session:
        await ingest.ingest_host(session, host)
        typer.echo("Ingest complete.")


@app.command()
@syncify
async def crawl(
    num_processes: int = typer.Option(None),
):
    typer.echo("Update TLD database.")
    update_tld_names()
    typer.echo("Run queue processing.")

    queue_settings = QueueSettings(num_processes=num_processes, lookup_block_size=num_processes * 4)

    runner = QueueRunner("ingest", reader=ingest_host, writer=get_next_instance, settings=queue_settings)
    await runner.main()


@app.command()
@syncify
async def profile_ingest(num_instances: int = typer.Option(5), sort_by: str = typer.Option("tottime")):
    import cProfile

    typer.echo("Update TLD database.")
    update_tld_names()
    typer.echo("Run queue processing.")

    from fedimapper.services import db_session

    async with db_session.get_session() as session:
        pr = cProfile.Profile()
        pr.enable()
        successes = 0
        numbers = 0
        while successes <= num_instances:
            async for instance in get_next_instance(1):
                numbers += 1
                print(f"Run {numbers}")
                if await ingest_host(session, instance):
                    successes += 1
        pr.disable()
        pr.print_stats(sort=sort_by)


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


@app.command()
def word_test(language="english", message="The little brown dog did stuff."):
    from fedimapper.services import stopwords

    print(stopwords.get_key_words(language, message))


@app.command()
def asn_test():
    from tabulate import tabulate

    from fedimapper.services.networking import clean_asn_company

    output = []
    with open("network_list.json") as fp:
        networks = json.load(fp)
        for asn, network in networks["network"].items():
            output.append([asn, clean_asn_company(network["owner"]), network["owner"]])
    print(tabulate(output))


if __name__ == "__main__":
    app()
