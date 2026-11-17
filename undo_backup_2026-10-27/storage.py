from django.core.files.storage import Storage
import os
from supabase import create_client, Client

class SupabaseStorage(Storage):
    def __init__(self):
        from django.conf import settings
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.bucket_name = getattr(settings, 'SUPABASE_BUCKET_NAME', 'avatars')
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

    _save_called = False

    def _save(self, name, content):
        content_type = getattr(content, 'content_type', 'image/jpeg')
        try:
            file_bytes = content.read()
            self.client.storage.from_(self.bucket_name).upload(
                path=name,
                file=file_bytes,
                file_options={
                    "content-type": content_type,
                    "cache-control": "3600",
                    "upsert": "true"
                }
            )
        except Exception as e:
            print(f"Supabase upload error: {e}")
            raise e
        return name

    def _open(self, name, mode='rb'):
        pass

    def exists(self, name):
        return False

    def url(self, name):
        if not name:
            return ""
        cleaned_name = str(name).lstrip('/')
        if cleaned_name.startswith(f"{self.bucket_name}/"):
            cleaned_name = cleaned_name[len(self.bucket_name)+1:]
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{cleaned_name}"
