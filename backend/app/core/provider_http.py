import json
from typing import Any

import httpx

_RESPONSE_CHUNK_BYTES = 64 * 1024


def post_bounded_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    max_response_bytes: int,
) -> dict[str, Any]:
    with httpx.stream(
        "POST",
        url,
        json=payload,
        headers=headers,
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_bytes(chunk_size=_RESPONSE_CHUNK_BYTES):
            if len(content) + len(chunk) > max_response_bytes:
                raise ValueError("Provider response exceeds the configured limit.")
            content.extend(chunk)
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("Provider response must be a JSON object.")
    return parsed
