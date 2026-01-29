from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass(frozen=True)
class FeishuAuthConfig:
    base_url: str
    app_id: str
    app_secret: str


class FeishuClient:
    def __init__(self, config: FeishuAuthConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._token: Optional[str] = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()

    def get_doc_raw_content(self, document_id: str) -> str:
        token = self._get_tenant_access_token()
        url = (
            f"{self._config.base_url.rstrip('/')}"
            f"/open-apis/docx/v1/documents/{document_id}/raw_content"
        )
        response = self._session.get(url, headers=self._auth_headers(token), timeout=10)
        data = self._read_response(response)
        content = (
            data.get("data", {}).get("content")
            or data.get("data", {}).get("raw_content")
            or data.get("content")
        )
        if not content:
            raise RuntimeError("feishu doc content missing")
        return str(content)

    def get_legacy_doc_raw_content(self, doc_token: str) -> str:
        token = self._get_tenant_access_token()
        url = (
            f"{self._config.base_url.rstrip('/')}"
            f"/open-apis/doc/v2/{doc_token}/raw_content"
        )
        response = self._session.get(url, headers=self._auth_headers(token), timeout=10)
        data = self._read_response(response)
        content = data.get("data", {}).get("content") or data.get("content")
        if not content:
            raise RuntimeError("feishu legacy doc content missing")
        return str(content)

    def get_wiki_node(self, wiki_token: str) -> dict:
        token = self._get_tenant_access_token()
        url = (
            f"{self._config.base_url.rstrip('/')}"
            "/open-apis/wiki/v2/spaces/get_node"
        )
        response = self._session.get(
            url,
            headers=self._auth_headers(token),
            params={"token": wiki_token},
            timeout=10,
        )
        data = self._read_response(response)
        node = data.get("data", {}).get("node")
        if not node:
            raise RuntimeError("feishu wiki node missing")
        return node

    def reply_text(self, message_id: str, text: str) -> None:
        token = self._get_tenant_access_token()
        url = (
            f"{self._config.base_url.rstrip('/')}"
            f"/open-apis/im/v1/messages/{message_id}/reply"
        )
        payload = {
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        response = self._session.post(
            url, headers=self._auth_headers(token), json=payload, timeout=10
        )
        self._read_response(response)

    def _auth_headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _get_tenant_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at:
            return self._token

        with self._lock:
            now = time.time()
            if self._token and now < self._token_expires_at:
                return self._token

            url = (
                f"{self._config.base_url.rstrip('/')}"
                "/open-apis/auth/v3/tenant_access_token/internal"
            )
            payload = {"app_id": self._config.app_id, "app_secret": self._config.app_secret}
            response = self._session.post(url, json=payload, timeout=10)
            data = self._read_response(response)
            token = data.get("tenant_access_token")
            expire = int(data.get("expire", 0))
            if not token:
                raise RuntimeError("feishu tenant_access_token missing")
            # Refresh a bit earlier than actual expiry.
            self._token = token
            self._token_expires_at = time.time() + max(0, expire - 60)
            return token

    def _read_response(self, response: requests.Response) -> dict:
        if response.status_code >= 400:
            print(f"!!! 飞书接口报错详情: {response.text}")
            raise RuntimeError(
                f"feishu error: status {response.status_code}, detail: {response.text}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("feishu error: invalid json") from exc

        code = data.get("code")
        if code not in (None, 0):
            msg = data.get("msg") or "unknown error"
            raise RuntimeError(f"feishu error: {code} {msg}")
        return data
