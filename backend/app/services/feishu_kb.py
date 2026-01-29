from __future__ import annotations

import math
import re
import threading
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from ..config import Settings
from ..integrations.feishu import FeishuAuthConfig, FeishuClient


@dataclass(frozen=True)
class KnowledgeSource:
    label: str
    token: str
    source_type: str


@dataclass(frozen=True)
class KnowledgeChunk:
    source: KnowledgeSource
    content: str
    tokens: Dict[str, int]
    length: int


@dataclass(frozen=True)
class RetrievalResult:
    source: KnowledgeSource
    content: str
    score: float


class FeishuKnowledgeBase:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = bool(settings.feishu_kb_sources)
        self._client = FeishuClient(
            FeishuAuthConfig(
                base_url=settings.feishu_base_url,
                app_id=settings.feishu_app_id,
                app_secret=settings.feishu_app_secret,
            )
        )
        self._lock = threading.Lock()
        self._chunks: List[KnowledgeChunk] = []
        self._idf: Dict[str, float] = {}
        self._avg_len = 0.0
        self._built_at = 0.0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def search(self, query: str) -> List[RetrievalResult]:
        if not self._enabled:
            return []
        self._ensure_index()
        tokens = _tokenize(query)
        if not tokens or not self._chunks:
            return []
        scores = []
        token_counts = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1
        for chunk in self._chunks:
            score = _bm25_score(
                token_counts,
                chunk.tokens,
                chunk.length,
                self._avg_len,
                self._idf,
            )
            if score >= self._settings.feishu_kb_min_score:
                scores.append(
                    RetrievalResult(
                        source=chunk.source,
                        content=chunk.content,
                        score=score,
                    )
                )
        scores.sort(key=lambda item: item.score, reverse=True)
        return scores[: self._settings.feishu_kb_top_k]

    def _ensure_index(self) -> None:
        now = time.time()
        if self._chunks and (now - self._built_at) < self._settings.feishu_kb_refresh_every:
            return
        with self._lock:
            now = time.time()
            if self._chunks and (now - self._built_at) < self._settings.feishu_kb_refresh_every:
                return
            self._build_index()
            self._built_at = time.time()

    def _build_index(self) -> None:
        sources = _parse_sources(self._settings.feishu_kb_sources)
        chunks: List[KnowledgeChunk] = []
        for source in sources:
            try:
                content = self._fetch_source_content(source)
            except Exception:
                continue
            content = _normalize_text(content)
            if not content:
                continue
            trimmed = _trim_text(content, self._settings.feishu_kb_max_doc_chars)
            for chunk in _chunk_text(
                trimmed,
                self._settings.feishu_kb_chunk_size,
                self._settings.feishu_kb_chunk_overlap,
            ):
                tokens = _count_tokens(chunk)
                if not tokens:
                    continue
                chunks.append(
                    KnowledgeChunk(
                        source=source,
                        content=chunk,
                        tokens=tokens,
                        length=sum(tokens.values()),
                    )
                )
        self._chunks = chunks
        self._idf, self._avg_len = _build_idf(chunks)

    def _fetch_source_content(self, source: KnowledgeSource) -> str:
        if source.source_type == "docx":
            return self._client.get_doc_raw_content(source.token)
        if source.source_type == "doc":
            return self._client.get_legacy_doc_raw_content(source.token)
        if source.source_type == "wiki":
            node = self._client.get_wiki_node(source.token)
            obj_type = str(node.get("obj_type", "")).lower()
            obj_token = str(node.get("obj_token", "")).strip()
            if not obj_token:
                raise RuntimeError("wiki node missing obj_token")
            if obj_type == "docx":
                return self._client.get_doc_raw_content(obj_token)
            if obj_type == "doc":
                return self._client.get_legacy_doc_raw_content(obj_token)
            raise RuntimeError(f"unsupported wiki obj_type: {obj_type}")
        raise RuntimeError(f"unsupported source type: {source.source_type}")


def _parse_sources(raw: str) -> List[KnowledgeSource]:
    sources: List[KnowledgeSource] = []
    for item in [entry.strip() for entry in raw.split(",") if entry.strip()]:
        label, token = _split_label(item)
        source_type, token = _parse_source_token(token)
        sources.append(
            KnowledgeSource(
                label=label or token,
                token=token,
                source_type=source_type,
            )
        )
    return sources


def _split_label(text: str) -> Tuple[str, str]:
    if "::" in text:
        label, token = text.split("::", 1)
        return label.strip(), token.strip()
    return "", text.strip()


def _parse_source_token(text: str) -> Tuple[str, str]:
    match = _DOCX_URL_RE.search(text)
    if match:
        return "docx", match.group(1)
    match = _WIKI_URL_RE.search(text)
    if match:
        return "wiki", match.group(1)
    if text.startswith("dox"):
        return "docx", text
    if text.startswith("doc"):
        return "doc", text
    if text.startswith("wik"):
        return "wiki", text
    raise RuntimeError(f"invalid feishu source: {text}")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()


def _trim_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _chunk_text(text: str, chunk_size: int, overlap: int) -> Iterable[str]:
    if chunk_size <= 0:
        if text:
            yield text
        return
    start = 0
    length = len(text)
    while start < length:
        end = min(length, start + chunk_size)
        chunk = text[start:end]
        if end < length:
            cut = _find_sentence_break(chunk)
            if cut is not None:
                end = start + cut
                chunk = text[start:end]
        chunk = chunk.strip()
        if chunk:
            yield chunk
        if end >= length:
            break
        start = max(0, end - max(overlap, 0))


def _find_sentence_break(chunk: str) -> Optional[int]:
    boundaries = ["。", "！", "？", ".", "!", "?", ";", "；"]
    candidates = [chunk.rfind(boundary) for boundary in boundaries]
    cut = max(candidates)
    if cut <= 0:
        return None
    if cut < len(chunk) * 0.6:
        return None
    return cut + 1


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for match in re.finditer(r"[a-zA-Z0-9]+", text.lower()):
        tokens.append(match.group())
    for char in text:
        if _is_cjk(char):
            tokens.append(char)
    return tokens


def _is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def _count_tokens(text: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for token in _tokenize(text):
        counts[token] = counts.get(token, 0) + 1
    return counts


def _build_idf(chunks: List[KnowledgeChunk]) -> Tuple[Dict[str, float], float]:
    if not chunks:
        return {}, 0.0
    doc_count = len(chunks)
    df: Dict[str, int] = {}
    total_len = 0
    for chunk in chunks:
        total_len += chunk.length
        for token in chunk.tokens.keys():
            df[token] = df.get(token, 0) + 1
    idf: Dict[str, float] = {}
    for token, freq in df.items():
        idf[token] = math.log1p((doc_count - freq + 0.5) / (freq + 0.5))
    avg_len = total_len / max(doc_count, 1)
    return idf, avg_len


def _bm25_score(
    query_tokens: Dict[str, int],
    doc_tokens: Dict[str, int],
    doc_len: int,
    avg_len: float,
    idf: Dict[str, float],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    score = 0.0
    denom_base = k1 * (1 - b + b * (doc_len / max(avg_len, 1.0)))
    for token, qf in query_tokens.items():
        tf = doc_tokens.get(token, 0)
        if tf == 0:
            continue
        token_idf = idf.get(token, 0.0)
        norm = tf + denom_base
        score += token_idf * ((tf * (k1 + 1)) / norm) * qf
    return score


_DOCX_URL_RE = re.compile(r"/docx/([a-zA-Z0-9]+)")
_WIKI_URL_RE = re.compile(r"/wiki/([a-zA-Z0-9]+)")
