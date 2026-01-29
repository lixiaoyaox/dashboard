from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class DeepSeekConfig:
    base_url: str
    api_key: str
    model: str
    embed_base_url: str
    embed_model: str


class DeepSeekClient:
    def __init__(self, config: DeepSeekConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._timeout = 20

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = f"{self._config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.4,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                response = self._session.post(
                    endpoint, json=payload, headers=headers, timeout=self._timeout
                )
                if response.status_code >= 400:
                    try:
                        body = response.json()
                        message = body.get("error", {}).get("message")
                    except Exception:
                        message = None
                    if message:
                        raise RuntimeError(f"deepseek error: {message}")
                    raise RuntimeError(f"deepseek error: status {response.status_code}")

                data = response.json()
                choices = data.get("choices") or []
                if not choices:
                    raise RuntimeError("deepseek returned no choices")
                content = choices[0].get("message", {}).get("content")
                if not content:
                    raise RuntimeError("deepseek returned empty content")
                return str(content)
            except Exception as exc:  # pragma: no cover - best effort retries
                last_error = exc
                if attempt < 3:
                    time.sleep(attempt)
                else:
                    break
        raise RuntimeError(str(last_error) if last_error else "deepseek request failed")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        endpoint = f"{self._config.embed_base_url.rstrip('/')}/embeddings"
        payload = {
            "model": self._config.embed_model,
            "input": texts,
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                response = self._session.post(
                    endpoint, json=payload, headers=headers, timeout=self._timeout
                )
                if response.status_code >= 400:
                    try:
                        body = response.json()
                        message = body.get("error", {}).get("message")
                    except Exception:
                        message = None
                    if message:
                        raise RuntimeError(f"deepseek error: {message}")
                    raise RuntimeError(f"deepseek error: status {response.status_code}")

                data = response.json()
                items = data.get("data") or []
                if not items:
                    raise RuntimeError("deepseek returned no embeddings")
                embeddings_by_index: dict[int, list[float]] = {}
                for item in items:
                    embedding = item.get("embedding")
                    if embedding is None:
                        continue
                    index = int(item.get("index", len(embeddings_by_index)))
                    embeddings_by_index[index] = embedding
                if not embeddings_by_index:
                    raise RuntimeError("deepseek returned empty embeddings")
                return [embeddings_by_index[i] for i in sorted(embeddings_by_index.keys())]
            except Exception as exc:  # pragma: no cover - best effort retries
                last_error = exc
                if attempt < 3:
                    time.sleep(attempt)
                else:
                    break
        raise RuntimeError(str(last_error) if last_error else "deepseek request failed")

