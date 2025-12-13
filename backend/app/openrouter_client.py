from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal

import httpx
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .config import Settings


class OpenRouterError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _extract_error_message(payload: Any) -> str | None:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            msg = err.get("message")
            if code is not None and msg:
                return f"{code}: {msg}"
            if msg:
                return str(msg)
    return None


ChatRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str


class OpenRouterClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not set")
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url.rstrip("/"),
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": settings.openrouter_http_referer,
                "X-Title": settings.openrouter_x_title,
                "Content-Type": "application/json",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=4.0))
    async def embeddings(self, *, model: str, inputs: list[str]) -> np.ndarray:
        """
        Returns float32 ndarray of shape (len(inputs), embedding_dim).
        """
        resp = await self._client.post(
            "/embeddings",
            json={
                "model": model,
                "input": inputs,
                # Explicit "float" for portability. (OpenRouter may support base64 too.)
                "encoding_format": "float",
            },
        )
        payload: Any
        try:
            payload = resp.json()
        except Exception:  # noqa: BLE001
            payload = None

        if resp.status_code != 200:
            msg = _extract_error_message(payload) or f"HTTP {resp.status_code} from embeddings"
            raise OpenRouterError(msg, status_code=resp.status_code)

        # OpenRouter may return status 200 with an error payload in rare cases.
        embedded_error = _extract_error_message(payload)
        if embedded_error:
            raise OpenRouterError(embedded_error, status_code=resp.status_code)

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list) or not data:
            raise OpenRouterError("Embeddings response missing data[]")

        vectors: list[list[float]] = []
        for item in data:
            if not isinstance(item, dict) or "embedding" not in item:
                raise OpenRouterError("Embeddings response item missing embedding")
            vectors.append(item["embedding"])

        arr = np.asarray(vectors, dtype=np.float32)
        return arr

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=4.0))
    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        resp = await self._client.post("/chat/completions", json=body)
        payload: Any
        try:
            payload = resp.json()
        except Exception:  # noqa: BLE001
            payload = None

        if resp.status_code != 200:
            msg = _extract_error_message(payload) or f"HTTP {resp.status_code} from chat"
            raise OpenRouterError(msg, status_code=resp.status_code)

        embedded_error = _extract_error_message(payload)
        if embedded_error:
            raise OpenRouterError(embedded_error, status_code=resp.status_code)

        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            # OpenRouter might return an "error" payload with status 200 in rare cases.
            msg = _extract_error_message(payload) or "Chat response missing choices[]"
            raise OpenRouterError(msg, status_code=resp.status_code)

        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(msg, dict):
            raise OpenRouterError("Chat response missing choices[0].message")
        content = msg.get("content")
        if not isinstance(content, str):
            raise OpenRouterError("Chat response missing choices[0].message.content")
        return content.strip()

    async def translate_query_for_doc_language(
        self, *, query: str, doc_language: str
    ) -> str:
        """
        Phase 1: Query Expansion (Language Alignment).
        Per spec: output ONLY the translated query string.
        """
        system = (
            "You are a translation engine. Detect the dominant language of the user's query "
            "and the document. If they differ, translate the query into the document's language "
            "for better keyword matching. Output ONLY the translated query string."
        )
        user = f"Document language: {doc_language}\nUser query: {query}"
        translated = await self.chat_completion(
            model=self.settings.chat_model,
            messages=[ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            temperature=0.0,
        )
        # Defensive cleanup: keep it as a single line string when possible.
        cleaned = " ".join(translated.split())
        return cleaned or query

    async def close_after_idle(self, *, idle_seconds: float = 0.0) -> None:
        if idle_seconds > 0:
            await asyncio.sleep(idle_seconds)
        await self.aclose()
