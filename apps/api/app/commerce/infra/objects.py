"""Validated image objects in deployment-controlled local storage or S3."""

import asyncio
import re
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4

from app.commerce.core.errors import MallError

OBJECT_KEY = re.compile(r"^[a-f0-9-]+\.(png|jpg|gif|webp)$")
IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}
PNG_HEADER = b"\x89PNG\r\n\x1a\n"
JPEG_HEADER = b"\xff\xd8\xff"
WEBP_TAG_START = 8
WEBP_TAG_END = 12


def image_key(data: bytes, *, content_type: str, maximum: int) -> str:
    if not data or len(data) > maximum:
        raise MallError("upload_size_invalid", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    valid = {
        "image/png": data.startswith(PNG_HEADER),
        "image/jpeg": data.startswith(JPEG_HEADER),
        "image/gif": data.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": data.startswith(b"RIFF") and data[WEBP_TAG_START:WEBP_TAG_END] == b"WEBP",
    }
    if not valid.get(content_type):
        raise MallError("upload_type_invalid", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    return str(uuid4()) + IMAGE_TYPES[content_type]


class LocalObjects:
    def __init__(self, settings):
        self.root, self.maximum = Path(settings.local_object_dir).resolve(), settings.max_upload_bytes

    def path(self, key: str) -> Path:
        if not OBJECT_KEY.fullmatch(key):
            raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
        path = (self.root / key).resolve()
        if path.parent != self.root:
            raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
        return path

    async def put(self, data: bytes, *, content_type: str):
        key = image_key(data, content_type=content_type, maximum=self.maximum)
        await asyncio.to_thread(self.root.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(self.path(key).write_bytes, data)
        return key

    async def url(self, key: str):
        self.path(key)
        return "/api/v1/mall/files/" + key


class S3Objects:
    def __init__(self, settings):
        self.settings = settings

    def _client(self, *, public: bool = False):
        import boto3
        from botocore.config import Config

        endpoint = self.settings.s3_public_endpoint if public else self.settings.s3_endpoint
        return boto3.client("s3", endpoint_url=endpoint or self.settings.s3_endpoint,
                            aws_access_key_id=self.settings.s3_access_key,
                            aws_secret_access_key=self.settings.s3_secret_key,
                            config=Config(connect_timeout=self.settings.external_timeout_seconds,
                                          read_timeout=self.settings.external_timeout_seconds,
                                          retries={"total_max_attempts": 1}))

    async def put(self, data: bytes, *, content_type: str):
        key = image_key(data, content_type=content_type, maximum=self.settings.max_upload_bytes)
        await asyncio.to_thread(self._client().put_object, Bucket=self.settings.s3_bucket,
                                Key=key, Body=data, ContentType=content_type)
        return key

    async def url(self, key: str):
        if not OBJECT_KEY.fullmatch(key):
            raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
        return await asyncio.to_thread(self._client(public=True).generate_presigned_url, "get_object",
                                        Params={"Bucket": self.settings.s3_bucket, "Key": key},
                                        ExpiresIn=self.settings.cache_ttl_seconds)
