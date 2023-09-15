import click


@click.group()
def cli():
    pass


@cli.command()
@click.argument("src")
def init(src):
    """sets the inital state of the project"""
    click.echo(f"setting base state for project: {src}")


@cli.command()
def add_dataset():
    """adds dataset to the project src"""
    click.echo("adding dataset to project")


@cli.command()
def get_datasets():
    pass


@cli.command()
def process_dataset():
    pass


@cli.command()
def sample():
    pass


@cli.command()
def classify():
    pass


if __name__ == "__main__":
    cli()
