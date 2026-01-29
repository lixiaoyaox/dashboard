from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from ..config import Settings
from ..integrations.feishu import FeishuAuthConfig, FeishuClient
from .vector_store import FeishuVectorStore


@dataclass(frozen=True)
class SourceRef:
    source_type: str
    token: str
    label: str


class FeishuDocumentIndexer:
    def __init__(self, settings: Settings, store: FeishuVectorStore) -> None:
        self._settings = settings
        self._store = store
        self._client = FeishuClient(
            FeishuAuthConfig(
                base_url=settings.feishu_base_url,
                app_id=settings.feishu_app_id,
                app_secret=settings.feishu_app_secret,
            )
        )

    def index_source(self, source_type: str, token: str, label: str = "") -> int:
        if not self._store.enabled:
            return 0
        content, label = self._fetch_content(source_type, token, label)
        if not content:
            return 0
        doc_id = f"{source_type}:{token}"
        final_label = label or token
        return self._store.upsert_document(
            doc_id=doc_id,
            label=final_label,
            content=content,
            source_type=source_type,
            token=token,
        )

    def delete_source(self, source_type: str, token: str) -> None:
        if not self._store.enabled:
            return
        doc_id = f"{source_type}:{token}"
        self._store.delete_document(doc_id)

    def _fetch_content(self, source_type: str, token: str, label: str) -> Tuple[str, str]:
        if source_type == "docx":
            return self._client.get_doc_raw_content(token), label
        if source_type == "doc":
            return self._client.get_legacy_doc_raw_content(token), label
        if source_type == "wiki":
            node = self._client.get_wiki_node(token)
            node_label = _extract_label(node) or label
            obj_type = str(node.get("obj_type", "")).lower()
            obj_token = str(node.get("obj_token", "")).strip()
            if not obj_token:
                raise RuntimeError("wiki node missing obj_token")
            if obj_type == "docx":
                return self._client.get_doc_raw_content(obj_token), node_label
            if obj_type == "doc":
                return self._client.get_legacy_doc_raw_content(obj_token), node_label
            raise RuntimeError(f"unsupported wiki obj_type: {obj_type}")
        raise RuntimeError(f"unsupported source type: {source_type}")


def _extract_label(node: dict) -> str:
    for key in ("title", "name", "obj_title", "node_title"):
        value = node.get(key)
        if value:
            return str(value).strip()
    return ""
