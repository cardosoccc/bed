import click

from bed.credentials import set_credential


@click.command("aws")
@click.option("--access-key-id", prompt=True, help="AWS Access Key ID")
@click.option("--secret-access-key", prompt=True, hide_input=True, help="AWS Secret Access Key")
def configure_aws(access_key_id, secret_access_key):
    """Configure AWS credentials for push/pull."""
    set_credential("aws_access_key_id", access_key_id)
    set_credential("aws_secret_access_key", secret_access_key)
    click.echo("aws credentials saved.")


@click.command("gcp")
@click.option("--key-path", prompt=True, help="Path to GCP service account key JSON file")
def configure_gcp(key_path):
    """Configure GCP credentials for push/pull."""
    set_credential("gcp_service_account_key_path", key_path)
    click.echo("gcp credentials saved.")
