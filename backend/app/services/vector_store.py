from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Iterable, List, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from ..config import Settings


@dataclass(frozen=True)
class VectorResult:
    doc_id: str
    label: str
    content: str
    score: float


class FeishuVectorStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = settings.feishu_kb_enabled
        self._lock = threading.Lock()
        self._client = chromadb.PersistentClient(path=settings.feishu_kb_persist_dir)
        embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=settings.feishu_kb_embed_model
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.feishu_kb_collection,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def upsert_document(
        self,
        doc_id: str,
        label: str,
        content: str,
        source_type: str,
        token: str,
    ) -> int:
        if not self._enabled:
            return 0
        normalized = _normalize_text(content)
        if not normalized:
            return 0
        trimmed = _trim_text(normalized, self._settings.feishu_kb_max_doc_chars)
        chunks = list(
            _chunk_text(
                trimmed,
                self._settings.feishu_kb_chunk_size,
                self._settings.feishu_kb_chunk_overlap,
            )
        )
        if not chunks:
            return 0
        metadatas = [
            {
                "doc_id": doc_id,
                "label": label,
                "source_type": source_type,
                "token": token,
            }
            for _ in chunks
        ]
        ids = [f"{doc_id}:{index}" for index in range(len(chunks))]
        with self._lock:
            self._collection.delete(where={"doc_id": doc_id})
            self._collection.add(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
            )
        return len(chunks)

    def delete_document(self, doc_id: str) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._collection.delete(where={"doc_id": doc_id})

    def search(self, query: str) -> List[VectorResult]:
        if not self._enabled:
            return []
        query = query.strip()
        if not query:
            return []
        with self._lock:
            result = self._collection.query(
                query_texts=[query],
                n_results=self._settings.feishu_kb_top_k,
            )
        return _to_results(result, self._settings.feishu_kb_min_score)


def _to_results(raw: dict, min_score: float) -> List[VectorResult]:
    documents = (raw.get("documents") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]
    distances = (raw.get("distances") or [[]])[0]
    results: List[VectorResult] = []
    for index, content in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        distance = distances[index] if index < len(distances) else None
        score = 0.0 if distance is None else 1.0 - float(distance)
        if score < min_score:
            continue
        doc_id = str(metadata.get("doc_id") or "")
        label = str(metadata.get("label") or doc_id or "doc")
        results.append(
            VectorResult(
                doc_id=doc_id,
                label=label,
                content=str(content),
                score=score,
            )
        )
    return results


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


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
    boundaries = [".", "!", "?", ";", "。", "！", "？", "；"]
    candidates = [chunk.rfind(boundary) for boundary in boundaries]
    cut = max(candidates)
    if cut <= 0:
        return None
    if cut < len(chunk) * 0.6:
        return None
    return cut + 1
