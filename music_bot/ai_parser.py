from __future__ import annotations

import json
import os
import re
from urllib.parse import urljoin

import httpx

from .dj_models import SearchIntent


class AIParser:
    """Parse DJ search language with an optional OpenAI-compatible endpoint."""

    def __init__(self, *, endpoint: str | None = None, api_key: str | None = None, model: str | None = None):
        self.endpoint = endpoint or os.getenv("AI_API_BASE_URL")
        self.api_key = api_key or os.getenv("AI_API_KEY")
        self.model = model or os.getenv("AI_MODEL", "gpt-4o-mini")

    def parse(self, query: str) -> SearchIntent:
        query = " ".join(query.split()).strip()
        if not query or len(query) > 200:
            raise ValueError("Search text must contain between 1 and 200 characters.")
        if self.endpoint and self.api_key:
            try:
                return self._parse_remote(query)
            except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass
        return parse_locally(query)

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
                    "Extract DJ music search filters as JSON. Keys: artist, title, genre, mood, "
                    "min_bpm, max_bpm, max_duration, instrumental. Use null when absent. "
                    f"Query: {query}"
                )}],
            },
            timeout=15,
        )
        response.raise_for_status()
        values = json.loads(response.json()["choices"][0]["message"]["content"])
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
    allowed_keys = {"artist", "title", "genre", "mood", "min_bpm", "max_bpm", "instrumental", "max_duration"}
    values = {key: value for key, value in values.items() if key in allowed_keys and value is not None}
    values["max_duration"] = min(int(values.get("max_duration", 900)), 900)
    return SearchIntent(raw_query=query, **values)


def provider_query(intent: SearchIntent) -> str:
    """Turn parsed DJ intent into a provider-friendly search query."""
    parts = [intent.artist, intent.title, intent.genre, intent.mood]
    if intent.min_bpm is not None:
        bpm = str(int(intent.min_bpm))
        parts.append(f"{bpm} bpm" if intent.max_bpm is None else f"{bpm}-{int(intent.max_bpm)} bpm")
    if intent.instrumental:
        parts.append("instrumental")
    query = " ".join(part for part in parts if part)
    return query or intent.raw_query
