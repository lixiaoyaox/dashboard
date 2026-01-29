from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from fastapi import BackgroundTasks

from ..config import Settings
from ..integrations.feishu import FeishuAuthConfig, FeishuClient
from .feishu_doc_indexer import FeishuDocumentIndexer


@dataclass(frozen=True)
class FeishuEventContext:
    message_id: str
    message_type: str
    text: str


class FeishuBotService:
    def __init__(self, settings: Settings, indexer: FeishuDocumentIndexer) -> None:
        self._settings = settings
        self._enabled = settings.feishu_bot_enabled
        self._client = FeishuClient(
            FeishuAuthConfig(
                base_url=settings.feishu_base_url,
                app_id=settings.feishu_app_id,
                app_secret=settings.feishu_app_secret,
            )
        )
        self._indexer = indexer

    def handle_message_event(self, message: dict, background_tasks: BackgroundTasks) -> None:
        if not self._enabled:
            return
        context = self._parse_message_context(message)
        if context is None:
            return
        background_tasks.add_task(self._process_message, context)

    def _process_message(self, context: FeishuEventContext) -> None:
        if context.message_type != "text":
            self._client.reply_text(
                context.message_id, "Please send a text message with a docx/wiki link."
            )
            return

        doc_token = _extract_doc_token(context.text)
        legacy_doc_token = _extract_legacy_doc_token(context.text)
        wiki_token = _extract_wiki_token(context.text)
        if not doc_token and not legacy_doc_token and not wiki_token:
            self._client.reply_text(
                context.message_id,
                "No document link found. Please paste a docx or wiki link.",
            )
            return

        try:
            if doc_token:
                self._indexer.index_source("docx", doc_token, "")
            elif legacy_doc_token:
                self._indexer.index_source("doc", legacy_doc_token, "")
            else:
                self._indexer.index_source("wiki", wiki_token, "")
        except Exception as exc:
            self._client.reply_text(context.message_id, f"Index failed: {exc}")
            return

        self._client.reply_text(context.message_id, "Document indexed. You can ask now.")

    def _parse_message_context(self, message: dict) -> Optional[FeishuEventContext]:
        message_id = message.get("message_id")
        if not message_id:
            return None
        message_type = message.get("message_type", "")
        raw_content = message.get("content") or "{}"
        try:
            content = json.loads(raw_content)
        except json.JSONDecodeError:
            content = {}
        text = str(content.get("text", "")).strip()
        return FeishuEventContext(
            message_id=message_id,
            message_type=message_type,
            text=text,
        )


_DOC_TOKEN_RE = re.compile(r"\b(dox[a-zA-Z0-9]+)\b")
_DOCX_URL_RE = re.compile(r"/docx/([a-zA-Z0-9]+)")
_WIKI_TOKEN_RE = re.compile(r"\b(wik[a-zA-Z0-9]+)\b")
_WIKI_URL_RE = re.compile(r"/wiki/([a-zA-Z0-9]+)")
_LEGACY_DOC_TOKEN_RE = re.compile(r"\b(doc[a-zA-Z0-9]+)\b")


def _extract_doc_token(text: str) -> Optional[str]:
    match = _DOCX_URL_RE.search(text)
    if match:
        return match.group(1)
    match = _DOC_TOKEN_RE.search(text)
    if match:
        return match.group(1)
    return None


def _extract_wiki_token(text: str) -> Optional[str]:
    match = _WIKI_URL_RE.search(text)
    if match:
        return match.group(1)
    match = _WIKI_TOKEN_RE.search(text)
    if match:
        return match.group(1)
    return None


def _extract_legacy_doc_token(text: str) -> Optional[str]:
    match = _LEGACY_DOC_TOKEN_RE.search(text)
    if match:
        return match.group(1)
    return None
