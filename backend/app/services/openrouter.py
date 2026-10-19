"""A small OpenRouter client. It sends chat requests and returns text; it never decides anything about the law.

The API key is only ever put in the Authorization header. It is never logged, and error messages never include it.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class AIError(Exception):
    """The AI call failed. `code` is one of: auth, credits, rate, timeout, network, server, bad_output."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class AIResponse:
    text: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


class OpenRouterClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.model = settings.openrouter_model
        self._base = settings.openrouter_base_url.rstrip("/")
        self._key = (settings.openrouter_api_key or "").strip()
        self._timeout = settings.openrouter_timeout_s
        self._transport = transport

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        json_schema: dict[str, Any] | None = None,
        schema_name: str = "result",
        max_tokens: int = 2500,
        attempts: int = 2,
    ) -> AIResponse:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "max_tokens": max_tokens}
        if json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
            }
        last: AIError | None = None
        for attempt in range(attempts):
            try:
                return self._post(body)
            except AIError as e:
                last = e
                # Only transient problems are worth one more try.
                if e.code not in {"rate", "timeout", "network", "server"} or attempt == attempts - 1:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise last or AIError("server", "The AI service did not answer.")

    def _post(self, body: dict[str, Any]) -> AIResponse:
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json", "X-Title": "Nirapod Fine"}
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                r = client.post(f"{self._base}/chat/completions", headers=headers, json=body)
        except httpx.TimeoutException:
            raise AIError("timeout", "The AI service took too long to answer.") from None
        except httpx.HTTPError:
            raise AIError("network", "Could not reach the AI service.") from None

        if r.status_code in (401, 403):
            raise AIError("auth", "The AI key was refused.")
        if r.status_code == 402:
            raise AIError("credits", "The AI account has no credit left.")
        if r.status_code == 429:
            raise AIError("rate", "The AI service is busy. Try again shortly.")
        if r.status_code >= 500:
            raise AIError("server", "The AI service had a problem.")
        if r.status_code >= 400:
            raise AIError("bad_output", f"The AI service rejected the request ({r.status_code}).")
        try:
            data = r.json()
            choice = data["choices"][0]
            text = choice["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError):
            # OpenRouter can report a provider failure inside a 200 response.
            raise AIError("server", "The AI service returned an unexpected answer.") from None
        if choice.get("finish_reason") == "length" and not text:
            raise AIError("bad_output", "The AI answer was cut off.")
        return AIResponse(text=text, model=str(data.get("model") or self.model), usage=data.get("usage") or {})


def get_client() -> OpenRouterClient | None:
    """The client to use, or None when no key is configured. Tests replace this function."""
    settings = get_settings()
    return OpenRouterClient(settings) if settings.ai_enabled else None


def parse_json(text: str) -> dict[str, Any]:
    """The model's JSON answer. Tolerates a code fence around it."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{") :] if "{" in t else t
    try:
        value = json.loads(t)
    except ValueError:
        raise AIError("bad_output", "The AI answer was not valid JSON.") from None
    if not isinstance(value, dict):
        raise AIError("bad_output", "The AI answer had the wrong shape.")
    return value
