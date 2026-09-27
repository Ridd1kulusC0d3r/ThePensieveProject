"""Deterministic extraction first; optional GLiNER for open-label NER."""

from __future__ import annotations

import ipaddress
import json
import re

from pensieve_timeline.osint.model import EntityMention
from pensieve_timeline.osint.normalize import normalize_label


DEFAULT_GLINER_LABELS = [
    "person",
    "organization",
    "location",
    "phone number",
    "email",
    "domain",
    "ip address",
    "url",
    "username",
    "social media handle",
    "cryptocurrency wallet",
]

PATTERNS = [
    ("email", re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.I)),
    ("url", re.compile(r"https?://[^\s<>\"']+", re.I)),
    ("ipv4", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")),
    ("ipv6", re.compile(r"(?<![A-Fa-f0-9:])(?:[A-Fa-f0-9]{0,4}:){2,7}[A-Fa-f0-9]{0,4}(?![A-Fa-f0-9:])")),
    ("phone", re.compile(r"(?<!\d)(?:\+?55[\s.-]?)?(?:\(?\d{2}\)?[\s.-]?)?(?:9?\d{4})[\s.-]?\d{4}(?!\d)")),
    ("social_handle", re.compile(r"(?<![\w@])@[A-Za-z0-9_][A-Za-z0-9_.-]{1,31}")),
    ("ethereum_wallet", re.compile(r"(?<![A-Fa-f0-9])0x[A-Fa-f0-9]{40}(?![A-Fa-f0-9])")),
    ("bitcoin_wallet", re.compile(r"(?<![A-Za-z0-9])(?:bc1[a-zA-HJ-NP-Z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})(?![A-Za-z0-9])")),
    ("sha256", re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{64}(?![A-Fa-f0-9])")),
    ("sha1", re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{40}(?![A-Fa-f0-9])")),
    ("md5", re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{32}(?![A-Fa-f0-9])")),
    ("cve", re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)),
    ("domain", re.compile(r"(?<![@\w.-])(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}(?![\w.-])")),
]


def _context(text: str, start: int, end: int, radius: int = 90) -> str:
    return text[max(0, start - radius):min(len(text), end + radius)].strip()


def _valid(label: str, value: str) -> bool:
    if label == "ipv4":
        try:
            return isinstance(ipaddress.ip_address(value), ipaddress.IPv4Address)
        except ValueError:
            return False
    if label == "ipv6":
        try:
            return isinstance(ipaddress.ip_address(value), ipaddress.IPv6Address)
        except ValueError:
            return False
    if label == "phone":
        return 10 <= len(re.sub(r"\D", "", value)) <= 13
    return True


def _trim_value(label: str, value: str) -> str:
    if label == "url":
        return value.rstrip(".,;:)]}")
    return value


def extract_patterns(event_id: str, text: str, source_field: str = "message") -> list[EntityMention]:
    output = []
    protected_ranges: list[tuple[int, int]] = []

    for label, pattern in PATTERNS:
        for match in pattern.finditer(text):
            value = _trim_value(label, match.group(0))
            end = match.start() + len(value)
            if not value or not _valid(label, value):
                continue

            if label == "domain" and any(
                match.start() >= start and end <= protected_end
                for start, protected_end in protected_ranges
            ):
                continue

            mention = EntityMention(
                event_id=event_id,
                text=value,
                label=label,
                start=match.start(),
                end=end,
                score=1.0,
                extractor=f"regex:{label}",
                source_field=source_field,
                context=_context(text, match.start(), end),
            )
            output.append(mention)

            if label in {"email", "url"}:
                protected_ranges.append((match.start(), end))

    return output


def _specialize_model_label(label: str, text: str) -> str:
    canonical = normalize_label(label)

    if canonical == "ip_address":
        try:
            parsed = ipaddress.ip_address(text)
            return "ipv4" if isinstance(parsed, ipaddress.IPv4Address) else "ipv6"
        except ValueError:
            return canonical

    if canonical == "crypto_wallet":
        if re.fullmatch(r"0x[A-Fa-f0-9]{40}", text):
            return "ethereum_wallet"
        if re.fullmatch(r"(?:bc1[a-zA-HJ-NP-Z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})", text):
            return "bitcoin_wallet"

    return canonical


class GlinerExtractor:
    def __init__(self, model_name="urchade/gliner_multi-v2.1", threshold=.45):
        try:
            from gliner import GLiNER
        except ImportError as exc:
            raise ValueError(
                "GLiNER opcional ausente; instale pensieve-timeline[osint]"
            ) from exc

        self.model_name = model_name
        self.threshold = threshold
        self.model = GLiNER.from_pretrained(model_name)

    def extract(self, event_id, text, labels, source_field="message"):
        output = []
        predictions = self.model.predict_entities(
            text,
            labels,
            threshold=self.threshold,
        )

        for prediction in predictions:
            try:
                start = int(prediction["start"])
                end = int(prediction["end"])
            except (KeyError, TypeError, ValueError):
                continue

            # The model may propose labels, but evidence text always comes from
            # the source span. Invalid or empty offsets are rejected.
            if start < 0 or end <= start or end > len(text):
                continue

            source_text = text[start:end]
            if not source_text.strip():
                continue

            label = _specialize_model_label(
                str(prediction.get("label", "entity")),
                source_text,
            )
            score = max(0.0, min(1.0, float(prediction.get("score", 0.0))))

            output.append(
                EntityMention(
                    event_id=event_id,
                    text=source_text,
                    label=label,
                    start=start,
                    end=end,
                    score=score,
                    extractor=f"gliner:{self.model_name}",
                    source_field=source_field,
                    context=_context(text, start, end),
                )
            )

        return output


def deduplicate_mentions(mentions) -> list[EntityMention]:
    """Merge equivalent extraction results while retaining corroborating extractors."""

    merged: dict[str, EntityMention] = {}
    rank = {"deterministic": 3, "model": 2, "derived": 1}

    for mention in mentions:
        current = merged.get(mention.mention_id)
        if current is None:
            merged[mention.mention_id] = mention
            continue

        extractors = sorted(
            set(current.corroborated_by)
            | set(mention.corroborated_by)
            | {current.extractor, mention.extractor}
        )

        current_rank = rank.get(current.confidence_kind, 0)
        candidate_rank = rank.get(mention.confidence_kind, 0)
        replace_primary = (
            candidate_rank > current_rank
            or (
                candidate_rank == current_rank
                and mention.score > current.score
            )
        )

        if replace_primary:
            mention.corroborated_by = extractors
            merged[mention.mention_id] = mention
        else:
            current.corroborated_by = extractors
            current.score = max(current.score, mention.score)

    return sorted(
        merged.values(),
        key=lambda mention: (
            mention.event_id,
            mention.source_field,
            mention.start,
            mention.label,
        ),
    )


def extract_entities(
    events,
    *,
    use_gliner=False,
    model_name="urchade/gliner_multi-v2.1",
    labels=None,
    threshold=.45,
    include_raw=False,
):
    gliner = GlinerExtractor(model_name, threshold) if use_gliner else None
    mentions = []

    for event in events:
        fields = [("message", event.message)]
        if include_raw and event.raw:
            fields.append(
                (
                    "raw",
                    json.dumps(
                        event.raw,
                        ensure_ascii=False,
                        default=str,
                    )[:8000],
                )
            )

        for source_field, text in fields:
            mentions.extend(
                extract_patterns(
                    event.event_id,
                    text,
                    source_field,
                )
            )

            if gliner:
                mentions.extend(
                    gliner.extract(
                        event.event_id,
                        text,
                        labels or DEFAULT_GLINER_LABELS,
                        source_field,
                    )
                )

    return deduplicate_mentions(mentions)
