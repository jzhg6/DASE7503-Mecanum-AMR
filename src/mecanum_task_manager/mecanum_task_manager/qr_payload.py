# Copyright (c) 2026 DASE7503 project contributors
# SPDX-License-Identifier: MIT
"""Pure-Python validation for transport-mission QR payloads."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re


_TOKEN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_ALIASES = {
    "id": "mission_id",
    "mission": "mission_id",
    "from": "pickup",
    "to": "dropoff",
}


@dataclass(frozen=True)
class TransportMission:
    mission_id: str
    pickup: str
    dropoff: str
    item: str = ""


def _parse_key_value(payload: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for pair in payload.split(";"):
        if not pair.strip():
            continue
        if ":" not in pair:
            raise ValueError(f"missing ':' in field: {pair!r}")
        key, value = pair.split(":", 1)
        normalized_key = _ALIASES.get(key.strip().lower(), key.strip().lower())
        result[normalized_key] = value.strip()
    return result


def _validate_token(name: str, value: object, *, required: bool = True) -> str:
    text = str(value).strip() if value is not None else ""
    if not text and not required:
        return ""
    if not _TOKEN.fullmatch(text):
        raise ValueError(
            f"{name} must contain 1-32 letters, digits, '_' or '-'"
        )
    return text


def parse_transport_mission(payload: str) -> TransportMission:
    """Parse JSON or semicolon-separated QR content into a validated mission."""
    if not isinstance(payload, str):
        raise ValueError("payload must be text")
    text = payload.strip()
    if not text or len(text) > 512:
        raise ValueError("payload must contain 1-512 characters")

    if text.startswith("{"):
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc.msg}") from exc
        if not isinstance(raw, dict):
            raise ValueError("JSON payload must be an object")
        data = {
            _ALIASES.get(str(key).lower(), str(key).lower()): value
            for key, value in raw.items()
        }
    else:
        data = _parse_key_value(text)

    missing = [key for key in ("mission_id", "pickup", "dropoff") if key not in data]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))

    return TransportMission(
        mission_id=_validate_token("mission_id", data["mission_id"]),
        pickup=_validate_token("pickup", data["pickup"]),
        dropoff=_validate_token("dropoff", data["dropoff"]),
        item=_validate_token("item", data.get("item", ""), required=False),
    )
