from __future__ import annotations

import hashlib
import re
from typing import Iterable, Optional, Set, Tuple

from fastapi import BackgroundTasks

from ..config import Settings
from .feishu_bot import FeishuBotService
from .feishu_doc_indexer import FeishuDocumentIndexer


class FeishuEventService:
    def __init__(
        self,
        settings: Settings,
        bot_service: Optional[FeishuBotService],
        indexer: FeishuDocumentIndexer,
    ) -> None:
        self._settings = settings
        self._bot = bot_service
        self._indexer = indexer
        self._enabled = settings.feishu_bot_enabled or settings.feishu_kb_enabled

    def handle_event(
        self,
        payload: dict,
        raw_body: bytes,
        headers: dict,
        background_tasks: BackgroundTasks,
    ) -> dict:
        if "challenge" in payload:
            return {"challenge": payload.get("challenge")}

        if not self._enabled:
            return {"ok": True}

        self._verify_token(payload)
        self._verify_signature(raw_body, headers)

        event_type = (payload.get("header") or {}).get("event_type") or payload.get("type")
        if event_type == "im.message.receive_v1" and self._bot:
            message = (payload.get("event") or {}).get("message") or {}
            self._bot.handle_message_event(message, background_tasks)
            return {"ok": True}

        sources = _extract_sources(payload)
        if not sources:
            return {"ok": True}

        if _is_delete_event(payload, event_type):
            for source_type, token in sources:
                background_tasks.add_task(self._indexer.delete_source, source_type, token)
        else:
            label = _extract_label_hint(payload)
            for source_type, token in sources:
                background_tasks.add_task(
                    self._indexer.index_source, source_type, token, label
                )
        return {"ok": True}

    def _verify_token(self, payload: dict) -> None:
        expected = self._settings.feishu_verification_token
        if not expected:
            return
        token = (payload.get("header") or {}).get("token") or payload.get("token")
        if token != expected:
            raise RuntimeError("feishu verification token mismatch")

    def _verify_signature(self, raw_body: bytes, headers: dict) -> None:
        encrypt_key = self._settings.feishu_encrypt_key
        if not encrypt_key:
            return
        timestamp = headers.get("X-Lark-Request-Timestamp")
        nonce = headers.get("X-Lark-Request-Nonce")
        signature = headers.get("X-Lark-Signature")
        if not timestamp or not nonce or not signature:
            raise RuntimeError("feishu signature headers missing")
        sign_payload = (timestamp + nonce + encrypt_key).encode("utf-8") + raw_body
        expected = hashlib.sha256(sign_payload).hexdigest()
        if signature != expected:
            raise RuntimeError("feishu signature mismatch")


_DOC_TOKEN_RE = re.compile(r"\b(dox[a-zA-Z0-9]+)\b")
_DOCX_URL_RE = re.compile(r"/docx/([a-zA-Z0-9]+)")
_WIKI_TOKEN_RE = re.compile(r"\b(wik[a-zA-Z0-9]+)\b")
_WIKI_URL_RE = re.compile(r"/wiki/([a-zA-Z0-9]+)")
_LEGACY_DOC_TOKEN_RE = re.compile(r"\b(doc[a-zA-Z0-9]+)\b")


def _extract_sources(payload: dict) -> Set[Tuple[str, str]]:
    sources: Set[Tuple[str, str]] = set()
    for text in _iter_strings(payload):
        for match in _DOCX_URL_RE.finditer(text):
            sources.add(("docx", match.group(1)))
        for match in _WIKI_URL_RE.finditer(text):
            sources.add(("wiki", match.group(1)))
        for match in _DOC_TOKEN_RE.finditer(text):
            sources.add(("docx", match.group(1)))
        for match in _WIKI_TOKEN_RE.finditer(text):
            sources.add(("wiki", match.group(1)))
        for match in _LEGACY_DOC_TOKEN_RE.finditer(text):
            sources.add(("doc", match.group(1)))
    return sources


def _iter_strings(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
    elif isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            yield cleaned


def _is_delete_event(payload: dict, event_type: Optional[str]) -> bool:
    if event_type:
        lowered = event_type.lower()
        for needle in ("delete", "deleted", "removed", "trash"):
            if needle in lowered:
                return True
    for key in ("is_deleted", "is_removed", "is_trashed", "deleted", "removed"):
        if _find_bool(payload, key):
            return True
    return False


def _find_bool(payload: dict, key: str) -> bool:
    for k, value in _iter_kv(payload):
        if k == key and isinstance(value, bool) and value:
            return True
    return False


def _iter_kv(value: object) -> Iterable[Tuple[str, object]]:
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from _iter_kv(v)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_kv(item)


def _extract_label_hint(payload: dict) -> str:
    for key in ("title", "name", "doc_title", "file_name"):
        for k, value in _iter_kv(payload):
            if k == key and isinstance(value, str) and value.strip():
                return value.strip()
    return ""
