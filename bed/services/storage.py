import json
from pathlib import Path

from bed.credentials import get_aws_credentials, get_gcp_credentials_path


def parse_bucket_url(url: str) -> tuple[str, str, str]:
    if url.startswith("s3://"):
        parts = url[5:].split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        return "s3", bucket, prefix
    elif url.startswith("gs://"):
        parts = url[5:].split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        return "gs", bucket, prefix
    raise ValueError(f"Unsupported bucket URL scheme: {url}")


class S3Provider:
    def __init__(self, bucket: str, prefix: str):
        import boto3

        self.bucket = bucket
        self.prefix = prefix
        aws_creds = get_aws_credentials()
        if aws_creds:
            self.client = boto3.client(
                "s3",
                aws_access_key_id=aws_creds[0],
                aws_secret_access_key=aws_creds[1],
            )
        else:
            self.client = boto3.client("s3")

    def _key(self, filename: str) -> str:
        return f"{self.prefix}/{filename}" if self.prefix else filename

    def upload(self, local_path: Path, filename: str) -> None:
        self.client.upload_file(str(local_path), self.bucket, self._key(filename))

    def download(self, filename: str, local_path: Path) -> None:
        self.client.download_file(self.bucket, self._key(filename), str(local_path))

    def read_json(self, filename: str) -> dict | None:
        try:
            import io

            buf = io.BytesIO()
            self.client.download_fileobj(self.bucket, self._key(filename), buf)
            buf.seek(0)
            return json.loads(buf.read().decode("utf-8"))
        except self.client.exceptions.NoSuchKey:
            return None
        except Exception:
            return None

    def upload_json(self, data: dict, filename: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._key(filename),
            Body=json.dumps(data).encode("utf-8"),
            ContentType="application/json",
        )


class GCSProvider:
    def __init__(self, bucket: str, prefix: str):
        from google.cloud import storage as gcs

        gcp_path = get_gcp_credentials_path()
        if gcp_path:
            self.client = gcs.Client.from_service_account_json(gcp_path)
        else:
            self.client = gcs.Client()
        self.bucket_obj = self.client.bucket(bucket)
        self.prefix = prefix

    def _key(self, filename: str) -> str:
        return f"{self.prefix}/{filename}" if self.prefix else filename

    def upload(self, local_path: Path, filename: str) -> None:
        blob = self.bucket_obj.blob(self._key(filename))
        blob.upload_from_filename(str(local_path))

    def download(self, filename: str, local_path: Path) -> None:
        blob = self.bucket_obj.blob(self._key(filename))
        blob.download_to_filename(str(local_path))

    def read_json(self, filename: str) -> dict | None:
        try:
            blob = self.bucket_obj.blob(self._key(filename))
            data = blob.download_as_bytes()
            return json.loads(data.decode("utf-8"))
        except Exception:
            return None

    def upload_json(self, data: dict, filename: str) -> None:
        blob = self.bucket_obj.blob(self._key(filename))
        blob.upload_from_string(
            json.dumps(data), content_type="application/json"
        )


def get_provider(bucket_url: str) -> S3Provider | GCSProvider:
    scheme, bucket, prefix = parse_bucket_url(bucket_url)
    if scheme == "s3":
        return S3Provider(bucket, prefix)
    elif scheme == "gs":
        return GCSProvider(bucket, prefix)
    raise ValueError(f"Unsupported scheme: {scheme}")
