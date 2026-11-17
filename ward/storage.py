import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class SupabasePrivateAvatarStorage(Storage):
    """Use local storage in development and private Supabase storage on Vercel."""

    def __init__(self, bucket_name="avatars", signed_url_ttl=3600):
        self.bucket_name = bucket_name
        self.signed_url_ttl = signed_url_ttl
        self._client = None
        self._local_storage = FileSystemStorage()

    @property
    def _use_supabase(self):
        vercel_flag = os.getenv("VERCEL", "").strip().lower()
        vercel_environment = os.getenv("VERCEL_ENV", "").strip().lower()
        return (
            vercel_flag in {"1", "true"}
            or bool(os.getenv("VERCEL_URL", "").strip())
            or vercel_environment in {"production", "preview", "development"}

        )

    @property
    def _supabase(self):
        if self._client is None:
            from supabase import create_client

            url = os.getenv("SUPABASE_URL", "")
            key = os.getenv("SUPABASE_SECRET_KEY", "")
            if not url or not key:
                raise RuntimeError(
                    "SUPABASE_URL and SUPABASE_SECRET_KEY must be configured "
                    "for avatar uploads on Vercel."
                )
            self._client = create_client(url, key)
        return self._client

    def _object_path(self, name):
        path = str(name).replace("\\", "/").lstrip("/")
        prefix = "avatars/"
        if path.startswith(prefix):
            path = path[len(prefix):]
        if not path or any(part in {".", ".."} for part in path.split("/")):
            raise ValueError("Invalid avatar storage path.")
        return path

    def _save(self, name, content):
        if not self._use_supabase:
            return self._local_storage._save(name, content)

        object_path = self._object_path(name)
        if hasattr(content, "seek"):
            content.seek(0)
        file_bytes = content.read()
        content_type = getattr(content, "content_type", None) or "application/octet-stream"

        self._supabase.storage.from_(self.bucket_name).upload(
            path=object_path,
            file=file_bytes,
            file_options={
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "false",
            },
        )
        return name

    def _open(self, name, mode="rb"):
        if not self._use_supabase:
            return self._local_storage._open(name, mode)

        data = self._supabase.storage.from_(self.bucket_name).download(
            self._object_path(name)
        )
        return ContentFile(data, name=name)

    def exists(self, name):
        if not self._use_supabase:
            return self._local_storage.exists(name)

        from storage3.exceptions import StorageApiError

        try:
            self._supabase.storage.from_(self.bucket_name).info(
                self._object_path(name)
            )
            return True
        except StorageApiError as exc:
            status = str(getattr(exc, "status", ""))
            code = str(getattr(exc, "code", "")).lower()
            message = str(getattr(exc, "message", "")).lower()
            if (
                status == "404"
                or code in {"404", "not_found", "object_not_found"}
                or "not found" in message
            ):
                return False
            raise

    def delete(self, name):
        if not name:
            return
        if not self._use_supabase:
            return self._local_storage.delete(name)

        self._supabase.storage.from_(self.bucket_name).remove(
            [self._object_path(name)]
        )

    def url(self, name):
        if not name:
            return ""
        if not self._use_supabase:
            return self._local_storage.url(name)

        response = self._supabase.storage.from_(self.bucket_name).create_signed_url(
            self._object_path(name),
            self.signed_url_ttl,
        )
        if isinstance(response, dict):
            signed_url = response.get("signedURL") or response.get("signedUrl")
        else:
            signed_url = (
                getattr(response, "signedURL", None)
                or getattr(response, "signedUrl", None)
            )

        if not signed_url:
            raise RuntimeError("Supabase did not return an avatar signed URL.")

        if signed_url.startswith(("https://", "http://")):
            return signed_url

        base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        if not base_url:
            raise RuntimeError("SUPABASE_URL must be configured for avatar signed URLs.")
        if signed_url.startswith("/storage/v1/"):
            return base_url + signed_url
        if signed_url.startswith("/"):
            return base_url + "/storage/v1" + signed_url
        return base_url + "/storage/v1/" + signed_url

    def size(self, name):
        if not self._use_supabase:
            return self._local_storage.size(name)

        info = self._supabase.storage.from_(self.bucket_name).info(
            self._object_path(name)
        )
        size = info.get("size")
        if size is None:
            size = (info.get("metadata") or {}).get("size")
        if size is None:
            raise NotImplementedError("Supabase did not return the avatar size.")
        return int(size)
