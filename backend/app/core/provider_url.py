from ipaddress import ip_address
from urllib.parse import urlparse


def validate_provider_url(url: str, *, has_api_key: bool) -> str:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise ValueError("Provider URL is invalid.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Provider URL is invalid.")
    if parsed.scheme == "https":
        return url
    hostname = hostname.lower()
    try:
        is_loopback = ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = hostname == "localhost"
    if has_api_key or not is_loopback:
        raise ValueError(
            "Provider URLs must use HTTPS except for unauthenticated loopback endpoints."
        )
    return url
