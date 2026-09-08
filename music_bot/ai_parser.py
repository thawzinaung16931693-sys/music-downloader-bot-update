from __future__ import annotations

import json
import os
import re
import time
from urllib.parse import urljoin

import httpx

from .dj_models import SearchIntent


class ParseResult:
    def __init__(self, intent: SearchIntent, used_ai: bool, fallback_reason: str | None = None):
        self.intent = intent
        self.used_ai = used_ai
        self.fallback_reason = fallback_reason


def _decode_json_object(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        raise ValueError("AI response content must be text")
    content = value.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.I).strip()
    decoded = json.loads(content)
    if not isinstance(decoded, dict):
        raise ValueError("AI response must be a JSON object")
    return decoded


class AIParser:
    """Parse DJ search language with an optional OpenAI-compatible endpoint."""

    def __init__(self, *, endpoint: str | None = None, api_key: str | None = None, model: str | None = None):
        self.endpoint = endpoint or os.getenv("AI_API_BASE_URL")
        self.api_key = api_key or os.getenv("AI_API_KEY")
        self.model = model or os.getenv("AI_MODEL", "gpt-4o-mini")
        self.provider = os.getenv("AI_PROVIDER", "openai_compatible")
        self.timeout = float(os.getenv("AI_TIMEOUT_SECONDS", "45"))
        self.retries = max(0, int(os.getenv("AI_RETRIES", "1")))
        self.cache_seconds = max(0, int(os.getenv("AI_CACHE_SECONDS", "300")))
        self._cache: dict[str, tuple[float, ParseResult]] = {}

    def parse(self, query: str) -> ParseResult:
        query = " ".join(query.split()).strip()
        if not query or len(query) > 200:
            raise ValueError("Search text must contain between 1 and 200 characters.")
        if self.endpoint and self.api_key:
            try:
                return ParseResult(self._parse_remote(query), True)
            except httpx.TimeoutException:
                return ParseResult(parse_locally(query), False, "timeout")
            except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                return ParseResult(parse_locally(query), False, "invalid_response")
        return ParseResult(parse_locally(query), False, "not_configured")

    async def parse_async(self, query: str) -> ParseResult:
        """Parse without blocking the Telegram event loop."""
        query = " ".join(query.split()).strip()
        if not query or len(query) > 200:
            raise ValueError("Search text must contain between 1 and 200 characters.")
        cached = self._cache.get(query.casefold())
        if cached and time.monotonic() - cached[0] < self.cache_seconds:
            return cached[1]
        if not self.endpoint or not self.api_key:
            return ParseResult(parse_locally(query), False, "not_configured")
        for attempt in range(self.retries + 1):
            try:
                result = ParseResult(await self._parse_remote_async(query), True)
                self._cache[query.casefold()] = (time.monotonic(), result)
                return result
            except httpx.TimeoutException:
                reason = "timeout"
            except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                reason = "invalid_response"
            if attempt < self.retries:
                await __import__("asyncio").sleep(1.5 * (attempt + 1))
        return ParseResult(parse_locally(query), False, reason)

    def _parse_remote(self, query: str) -> SearchIntent:
        endpoint = urljoin(self.endpoint.rstrip("/") + "/", "chat/completions")
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": (
                    "You are a strict music search parser, not a recommender. Extract only facts "
                    "explicitly present in the user's query. Never translate, replace, broaden, "
                    "or invent a language, country, artist, title, genre, mood, or version. "
                    "Preserve terms such as Myanmar, Burmese, popular, house, remix, live, "
                    "instrumental, and extended mix. Return JSON only with keys artist, title, "
                    "genre, mood, language, region, version, popularity, min_bpm, max_bpm, "
                    "max_duration, instrumental, keywords. "
                    "Put important original terms that do not fit another field in keywords. "
                    "Use null or [] when absent. Original user query: "
                    f"{query}"
                )}],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        values = _decode_json_object(response.json()["choices"][0]["message"]["content"])
        return _intent_from_values(query, values)

    async def _parse_remote_async(self, query: str) -> SearchIntent:
        if self.provider == "gemini":
            return await self._parse_gemini_async(query)
        endpoint = urljoin(self.endpoint.rstrip("/") + "/", "chat/completions")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": (
                        "You are a strict music search parser, not a recommender. Extract only facts "
                        "explicitly present in the user's query. Never translate, replace, broaden, "
                        "or invent a language, country, artist, title, genre, mood, or version. "
                        "Preserve terms such as Myanmar, Burmese, popular, house, remix, live, "
                        "instrumental, and extended mix. Return JSON only with keys artist, title, "
                        "genre, mood, language, region, version, popularity, min_bpm, max_bpm, "
                        "max_duration, instrumental, keywords. "
                        "Put important original terms that do not fit another field in keywords. "
                        "Use null or [] when absent. Original user query: "
                        f"{query}"
                    )}],
                },
            )
            response.raise_for_status()
            values = _decode_json_object(response.json()["choices"][0]["message"]["content"])
            return _intent_from_values(query, values)

    async def _parse_gemini_async(self, query: str) -> SearchIntent:
        endpoint = self.endpoint.rstrip("/")
        if not endpoint.endswith(":generateContent"):
            endpoint = f"{endpoint}/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                endpoint,
                headers={"Content-Type": "application/json", "X-goog-api-key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": (
                        "You are a strict music search parser, not a recommender. Extract only facts "
                        "explicitly present in the user's query. Never translate, replace, broaden, "
                        "or invent a language, country, artist, title, genre, mood, or version. "
                        "Return JSON only with keys artist, title, genre, mood, language, region, "
                        "version, popularity, min_bpm, max_bpm, max_duration, instrumental, "
                        "keywords. Original user query: "
                        f"{query}"
                    )}]}],
                    "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
                },
            )
            response.raise_for_status()
            values = _decode_json_object(response.json()["candidates"][0]["content"]["parts"][0]["text"])
            return _intent_from_values(query, values)


def parse_locally(query: str) -> SearchIntent:
    values: dict[str, object] = {}
    bpm = re.search(r"(?:between\s+)?(\d{2,3})\s*(?:-|to)\s*(\d{2,3})\s*bpm", query, re.I)
    if bpm:
        values["min_bpm"], values["max_bpm"] = float(bpm.group(1)), float(bpm.group(2))
    else:
        one_bpm = re.search(r"(\d{2,3})\s*bpm", query, re.I)
        if one_bpm:
            values["min_bpm"] = values["max_bpm"] = float(one_bpm.group(1))
    minutes = re.search(r"(?:under|less than|max(?:imum)?|<)\s*(\d+)\s*(?:minutes?|min)", query, re.I)
    if minutes:
        values["max_duration"] = int(minutes.group(1)) * 60
    if re.search(r"\binstrumental|no vocals?\b", query, re.I):
        values["instrumental"] = True
    return _intent_from_values(query, values)


def _intent_from_values(query: str, values: dict[str, object]) -> SearchIntent:
    if not isinstance(values, dict):
        raise ValueError("AI intent must be a JSON object")
    normalized: dict[str, object] = {}
    keywords = values.get("keywords", [])
    if keywords is not None and (
        not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords)
    ):
        raise ValueError("keywords must be a list of text")
    if isinstance(keywords, list) and len(keywords) > 20:
        raise ValueError("too many AI keywords")
    normalized["keywords"] = tuple(
        " ".join(item.split()).strip()[:60] for item in keywords if item.strip()
    )
    for key in ("artist", "title", "genre", "mood", "language", "region", "version", "popularity"):
        value = values.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be text")
            value = " ".join(value.split()).strip()
            if value:
                normalized[key] = value[:100]

    for key in ("min_bpm", "max_bpm"):
        value = values.get(key)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key} must be a number")
            value = float(value)
            if not 40 <= value <= 240:
                raise ValueError(f"{key} must be between 40 and 240")
            normalized[key] = value
    if normalized.get("min_bpm") and normalized.get("max_bpm"):
        if normalized["min_bpm"] > normalized["max_bpm"]:
            raise ValueError("min_bpm cannot exceed max_bpm")

    instrumental = values.get("instrumental")
    if instrumental is not None:
        if not isinstance(instrumental, bool):
            raise ValueError("instrumental must be true or false")
        normalized["instrumental"] = instrumental

    duration = values.get("max_duration", 900)
    if duration is None:
        duration = 900
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise ValueError("max_duration must be a number")
    normalized["max_duration"] = min(max(int(duration), 1), 900)
    return SearchIntent(raw_query=query, **normalized)


def provider_query(intent: SearchIntent) -> str:
    """Turn parsed DJ intent into a provider-friendly search query."""
    parts = [
        intent.raw_query,
        intent.artist, intent.title, intent.language, intent.region, intent.genre,
        intent.mood, intent.version, intent.popularity, *intent.keywords,
    ]
    if _is_myanmar_intent(intent):
        parts.extend(("Myanmar", "Burmese", "Myanmar DJ"))
    if intent.min_bpm is not None:
        bpm = str(int(intent.min_bpm))
        parts.append(f"{bpm} bpm" if intent.max_bpm is None else f"{bpm}-{int(intent.max_bpm)} bpm")
    if intent.instrumental:
        parts.append("instrumental")
    return _dedupe_query_parts(parts)


def _dedupe_query_parts(parts: list[str | None]) -> str:
    """Keep every meaningful phrase once while preserving the user's wording."""
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        normalized = " ".join(part.split()).strip()
        words = normalized.casefold().split()
        if not normalized or all(word in seen for word in words):
            continue
        result.append(normalized)
        seen.update(words)
    return " ".join(result)


def _is_myanmar_intent(intent: SearchIntent) -> bool:
    values = " ".join(value or "" for value in (intent.language, intent.region, *intent.keywords, intent.raw_query)).casefold()
    return "myanmar" in values or "burmese" in values or "မြန်မာ" in values


def dj_source_plan(intent: SearchIntent) -> list[str]:
    """Build permitted DJ source candidates for the AI-assisted search flow."""
    query = provider_query(intent)
    return [f"ytsearch100:{query} audio", f"scsearch:{query}", f"bcsearch:{query}"]
