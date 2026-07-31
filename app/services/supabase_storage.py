import os
import re
import uuid
from typing import Any, Optional
from urllib.parse import quote, urlparse

import httpx

from app.core.config import settings


class SupabaseStorageError(RuntimeError):
    pass


class SupabaseStorage:
    """Small server-side adapter for private Supabase Storage objects."""

    def __init__(self) -> None:
        self.base_url = (settings.SUPABASE_URL or "").rstrip("/")
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_SECRET_KEY
        self.client_key = settings.SUPABASE_ANON_KEY or settings.SUPABASE_PUBLISHABLE_KEY
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.service_key and self.client_key and self.bucket)

    @property
    def project_ref(self) -> str:
        host = urlparse(self.base_url).hostname or ""
        return host.split(".")[0]

    def _headers(self) -> dict[str, str]:
        if not self.enabled:
            raise SupabaseStorageError("Supabase Storage no está configurado.")
        return {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            response = httpx.request(method, url, headers=self._headers(), timeout=30, **kwargs)
        except httpx.HTTPError as exc:
            raise SupabaseStorageError(f"No se pudo conectar con Supabase Storage: {exc}") from exc
        if response.is_error:
            detail = response.text[:500]
            raise SupabaseStorageError(f"Supabase Storage respondió HTTP {response.status_code}: {detail}")
        return response

    def ensure_bucket(self) -> None:
        url = f"{self.base_url}/storage/v1/bucket/{quote(self.bucket, safe='')}"
        response = httpx.get(url, headers=self._headers(), timeout=15)
        if response.status_code == 200:
            return
        if response.status_code not in (400, 404):
            raise SupabaseStorageError(f"No se pudo validar el bucket de documentos (HTTP {response.status_code}).")
        create_url = f"{self.base_url}/storage/v1/bucket"
        response = httpx.post(
            create_url,
            headers=self._headers(),
            json={"id": self.bucket, "name": self.bucket, "public": False},
            timeout=15,
        )
        if response.status_code not in (200, 201, 409):
            raise SupabaseStorageError(f"No se pudo crear el bucket privado (HTTP {response.status_code}).")

    @staticmethod
    def safe_object_name(name: str) -> str:
        name = os.path.basename(name or "archivo")
        name = re.sub(r"[^\w.\- ]", "_", name).strip() or "archivo"
        return name[:100]

    def make_object_path(self, filename: str) -> str:
        return f"documents/{uuid.uuid4().hex}/{self.safe_object_name(filename)}"

    def create_signed_upload(self, object_path: str) -> dict[str, str]:
        self.ensure_bucket()
        url = f"{self.base_url}/storage/v1/object/upload/sign/{quote(self.bucket, safe='')}/{quote(object_path, safe='/')}"
        response = self._request("POST", url, json={"upsert": False})
        payload = response.json()
        token = payload.get("token")
        if not token:
            raise SupabaseStorageError("Supabase no entregó el token temporal de carga.")
        signed_url = payload.get("url")
        if not signed_url:
            raise SupabaseStorageError("Supabase no entregó la URL temporal de carga.")
        return {
            "token": token,
            "upload_url": signed_url if signed_url.startswith("http") else f"{self.base_url}/storage/v1{signed_url}",
            "bucket": self.bucket,
            "path": object_path,
        }

    def object_exists(self, object_path: str, expected_size: int) -> bool:
        url = f"{self.base_url}/storage/v1/object/{quote(self.bucket, safe='')}/{quote(object_path, safe='/')}"
        response = httpx.head(url, headers=self._headers(), timeout=30)
        if response.status_code != 200:
            return False
        content_length = response.headers.get("content-length")
        return content_length is None or int(content_length) == expected_size

    def signed_download_url(self, object_path: str, expires_in: int = 300) -> str:
        url = f"{self.base_url}/storage/v1/object/sign/{quote(self.bucket, safe='')}/{quote(object_path, safe='/')}"
        response = self._request("POST", url, json={"expiresIn": expires_in})
        signed = response.json().get("signedURL") or response.json().get("signedUrl")
        if not signed:
            raise SupabaseStorageError("Supabase no entregó una URL temporal de descarga.")
        return signed if signed.startswith("http") else f"{self.base_url}/storage/v1{signed}"

    def delete_object(self, object_path: str) -> None:
        url = f"{self.base_url}/storage/v1/object/{quote(self.bucket, safe='')}/{quote(object_path, safe='/')}"
        response = httpx.request("DELETE", url.rsplit("/", 1)[0], headers=self._headers(), json={"prefixes": [object_path]}, timeout=30)
        if response.status_code not in (200, 204, 400, 404):
            raise SupabaseStorageError(f"No se pudo eliminar el objeto (HTTP {response.status_code}).")


supabase_storage = SupabaseStorage()
