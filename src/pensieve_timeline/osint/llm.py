"""Optional local Qwen adapter over Evidence Packet v2."""

from __future__ import annotations

import json
import re

from pensieve_timeline.reasoning import (
    build_evidence_packet_v2,
    immutable_packet_copy,
    snapshot_packet,
    validate_reasoning_payload,
)


SYSTEM_PROMPT = """You are an evidence-bounded DFIR and OSINT reasoning assistant.

Use only the supplied Evidence Packet v2.
Do not invent event IDs, people, ownership, identity, causality or intent.
A normalized entity is not a verified identity.
A correlation is not proof of causality.
Your output is derived analysis and must never rewrite evidence.

Return JSON only with exactly these top-level keys:
summary, claims, uncertainties, next_questions

Each claim must contain exactly:
level, statement, evidence_event_ids, rationale, alternatives, reported_confidence

Rules:
- level is observation, inference, or hypothesis.
- every claim cites one or more event IDs from the packet.
- observations have alternatives=[].
- hypotheses have at least one plausible alternative.
- reported_confidence is optional and is only model self-assessment, not probability.
- do not return events, corrected_events, raw evidence, patches, commands, or markdown.
"""


def build_evidence_packet(
    events,
    mentions,
    *,
    max_events=40,
    max_message_chars=700,
):
    """Backward-compatible entry point for Evidence Packet v2."""

    return build_evidence_packet_v2(
        events,
        mentions,
        max_events=max_events,
        max_message_chars=max_message_chars,
    )


def _strip_thinking(text: str) -> str:
    """Discard provider reasoning blocks instead of persisting them."""

    return re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()


def parse_model_json(text: str) -> dict:
    """Parse one JSON object and reject meaningful trailing content."""

    candidate = _strip_thinking(str(text).strip())
    fence = chr(96) * 3

    if candidate.startswith(fence):
        lines = candidate.splitlines()
        if lines and lines[0].lstrip().startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

    start = candidate.find("{")
    if start < 0:
        raise ValueError("model response did not contain a JSON object")

    decoder = json.JSONDecoder()
    try:
        payload, consumed = decoder.raw_decode(candidate[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"model returned invalid JSON: {exc}") from exc

    trailing = candidate[start + consumed :].strip()
    if trailing and trailing != fence:
        raise ValueError("model response contained trailing non-JSON content")
    if not isinstance(payload, dict):
        raise ValueError("model response JSON must be an object")
    return payload


def summarize_with_qwen(
    packet,
    *,
    model_name="Qwen/Qwen3-0.6B",
    max_new_tokens=1024,
):
    """Generate and validate a reasoning report without mutating evidence."""

    before = snapshot_packet(packet)
    provider_packet = immutable_packet_copy(packet)

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ValueError(
            "Qwen local opcional ausente; instale pensieve-timeline[llm]"
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto",
    )
    model.eval()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                provider_packet,
                ensure_ascii=False,
                sort_keys=True,
            ),
        },
    ]

    try:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    inputs = tokenizer([prompt], return_tensors="pt").to(model.device)
    generated = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    output_text = tokenizer.batch_decode(
        generated[:, inputs.input_ids.shape[1] :],
        skip_special_tokens=True,
    )[0]

    after = snapshot_packet(packet)
    if after != before:
        raise RuntimeError("evidence packet mutated during model execution")

    payload = parse_model_json(output_text)
    return validate_reasoning_payload(
        payload,
        packet,
        model_name=model_name,
    )
