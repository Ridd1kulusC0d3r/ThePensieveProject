"""Conservative normalization for evidence-bound OSINT entities.

Normalization is used for comparison and graph aggregation only. The original
text span is always preserved in EntityMention.text.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import SplitResult, urlsplit, urlunsplit


LABEL_ALIASES = {
    "person": "person",
    "people": "person",
    "organization": "organization",
    "organisation": "organization",
    "company": "organization",
    "location": "location",
    "phone": "phone",
    "phone_number": "phone",
    "telephone": "phone",
    "email": "email",
    "email_address": "email",
    "domain": "domain",
    "domain_name": "domain",
    "ip": "ip_address",
    "ip_address": "ip_address",
    "ipv4": "ipv4",
    "ipv6": "ipv6",
    "url": "url",
    "uri": "url",
    "username": "username",
    "user_name": "username",
    "social_media_handle": "social_handle",
    "social_handle": "social_handle",
    "handle": "social_handle",
    "cryptocurrency_wallet": "crypto_wallet",
    "crypto_wallet": "crypto_wallet",
    "ethereum_wallet": "ethereum_wallet",
    "bitcoin_wallet": "bitcoin_wallet",
    "md5": "md5",
    "sha1": "sha1",
    "sha256": "sha256",
    "cve": "cve",
}


def normalize_label(label: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", str(label).strip().casefold()).strip("_")
    return LABEL_ALIASES.get(value, value or "entity")


def _normalize_url(value: str) -> str:
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return value.strip()
    if not parts.scheme or not parts.netloc:
        return value.strip()

    hostname = parts.hostname.casefold() if parts.hostname else ""
    port = parts.port
    if port and not (
        (parts.scheme.casefold() == "http" and port == 80)
        or (parts.scheme.casefold() == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"

    if parts.username:
        auth = parts.username
        if parts.password:
            auth += f":{parts.password}"
        hostname = f"{auth}@{hostname}"

    normalized = SplitResult(
        parts.scheme.casefold(),
        hostname,
        parts.path or "",
        parts.query or "",
        parts.fragment or "",
    )
    return urlunsplit(normalized)


def normalize_value(label: str, value: str) -> str:
    """Return a comparison value without claiming a real-world identity."""

    canonical = normalize_label(label)
    text = " ".join(str(value).strip().split())

    if canonical in {"email", "domain", "username", "social_handle", "cve"}:
        return text.casefold()

    if canonical in {"ipv4", "ipv6", "ip_address"}:
        try:
            return ipaddress.ip_address(text).compressed.casefold()
        except ValueError:
            return text.casefold()

    if canonical == "phone":
        has_plus = text.lstrip().startswith("+")
        digits = re.sub(r"\D", "", text)
        return ("+" if has_plus else "") + digits

    if canonical == "url":
        return _normalize_url(text)

    if canonical in {"ethereum_wallet", "md5", "sha1", "sha256"}:
        return text.casefold()

    if canonical == "bitcoin_wallet" and text.casefold().startswith("bc1"):
        return text.casefold()

    return text


def confidence_kind(extractor: str) -> str:
    value = str(extractor).casefold()
    if value.startswith("regex"):
        return "deterministic"
    if value.startswith("gliner"):
        return "model"
    return "derived"
