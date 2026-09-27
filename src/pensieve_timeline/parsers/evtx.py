"""Optional python-evtx adapter with explicit EVTX provenance."""

from __future__ import annotations

import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

from pensieve_timeline.model import ForensicEvent, parse_timestamp
from pensieve_timeline.parsers.base import Parser


NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}


def _text(node):
    return node.text if node is not None and node.text is not None else None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _append_value(target: dict, key: str, value):
    """Preserve duplicate EventData/UserData fields instead of overwriting them."""

    if key not in target:
        target[key] = value
        return
    current = target[key]
    if isinstance(current, list):
        current.append(value)
    else:
        target[key] = [current, value]


def _event_data(root) -> dict:
    output = {}
    event_data = root.find("e:EventData", NS)
    if event_data is None:
        return output
    for position, item in enumerate(event_data.findall("e:Data", NS), start=1):
        key = item.attrib.get("Name") or f"Data{position}"
        _append_value(output, key, item.text)
    return output


def _user_data(root) -> dict:
    """Flatten UserData leaves while retaining duplicate keys."""

    output = {}
    user_data = root.find("e:UserData", NS)
    if user_data is None:
        return output

    for node in user_data.iter():
        if node is user_data:
            continue
        if list(node):
            continue
        value = node.text
        if value in (None, ""):
            continue
        _append_value(output, _local_name(node.tag), value)
    return output


def _system_fields(system) -> dict:
    provider_node = system.find("e:Provider", NS)
    time_node = system.find("e:TimeCreated", NS)
    execution_node = system.find("e:Execution", NS)
    security_node = system.find("e:Security", NS)
    correlation_node = system.find("e:Correlation", NS)

    return {
        "provider_name": (
            provider_node.attrib.get("Name")
            if provider_node is not None
            else None
        ),
        "provider_guid": (
            provider_node.attrib.get("Guid")
            if provider_node is not None
            else None
        ),
        "event_id": _text(system.find("e:EventID", NS)),
        "version": _text(system.find("e:Version", NS)),
        "level": _text(system.find("e:Level", NS)),
        "task": _text(system.find("e:Task", NS)),
        "opcode": _text(system.find("e:Opcode", NS)),
        "keywords": _text(system.find("e:Keywords", NS)),
        "time_created": (
            time_node.attrib.get("SystemTime")
            if time_node is not None
            else None
        ),
        "event_record_id": _text(system.find("e:EventRecordID", NS)),
        "channel": _text(system.find("e:Channel", NS)),
        "computer": _text(system.find("e:Computer", NS)),
        "execution_process_id": (
            execution_node.attrib.get("ProcessID")
            if execution_node is not None
            else None
        ),
        "execution_thread_id": (
            execution_node.attrib.get("ThreadID")
            if execution_node is not None
            else None
        ),
        "security_user_id": (
            security_node.attrib.get("UserID")
            if security_node is not None
            else None
        ),
        "activity_id": (
            correlation_node.attrib.get("ActivityID")
            if correlation_node is not None
            else None
        ),
        "related_activity_id": (
            correlation_node.attrib.get("RelatedActivityID")
            if correlation_node is not None
            else None
        ),
    }


def _first_value(mapping: dict, *keys):
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, list):
            value = next((item for item in value if item not in (None, "")), None)
        if value not in (None, ""):
            return value
    return None


def parse_evtx_xml(
    xml_text: str,
    *,
    source_path: str,
    fallback_index: int,
) -> ForensicEvent:
    """Normalize one EVTX record XML document into a ForensicEvent."""

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(
            f"{source_path}: EVTX record {fallback_index}: invalid XML"
        ) from exc

    system = root.find("e:System", NS)
    if system is None:
        raise ValueError(
            f"{source_path}: EVTX record {fallback_index}: missing System"
        )

    system_data = _system_fields(system)
    if not system_data["time_created"]:
        raise ValueError(
            f"{source_path}: EVTX record {fallback_index}: missing TimeCreated"
        )

    timestamp, assumption = parse_timestamp(system_data["time_created"])
    event_data = _event_data(root)
    user_data = _user_data(root)

    provider = system_data["provider_name"]
    code = system_data["event_id"]
    channel = system_data["channel"] or "Windows Event Log"
    record_id = system_data["event_record_id"] or str(fallback_index)

    user = _first_value(
        event_data,
        "SubjectUserName",
        "TargetUserName",
        "User",
        "UserName",
    ) or _first_value(
        user_data,
        "SubjectUserName",
        "TargetUserName",
        "User",
        "UserName",
    ) or system_data["security_user_id"]

    pid = _first_value(
        event_data,
        "ProcessId",
        "ProcessID",
        "NewProcessId",
    ) or _first_value(
        user_data,
        "ProcessId",
        "ProcessID",
        "NewProcessId",
    ) or system_data["execution_process_id"]

    detail_items = []
    for mapping in (event_data, user_data):
        for key, value in mapping.items():
            if value in (None, "", []):
                continue
            detail_items.append(f"{key}={value}")
            if len(detail_items) >= 12:
                break
        if len(detail_items) >= 12:
            break

    prefix = f"EventID {code or '?'}"
    if provider:
        prefix += f" | {provider}"
    message = prefix
    if detail_items:
        message += " | " + ", ".join(detail_items)

    xml_sha256 = hashlib.sha256(
        xml_text.encode("utf-8", errors="replace")
    ).hexdigest()

    return ForensicEvent(
        timestamp,
        channel,
        "evtx",
        message,
        host=system_data["computer"],
        user=str(user) if user not in (None, "") else None,
        event_type="windows_event",
        provider=provider,
        event_code=str(code) if code not in (None, "") else None,
        pid=str(pid) if pid not in (None, "") else None,
        record_locator=f"event_record_id:{record_id}",
        source_path=str(source_path),
        parser="python-evtx",
        parser_version="2",
        time_assumption=assumption,
        raw={
            "system": system_data,
            "event_data": event_data,
            "user_data": user_data,
            "xml_sha256": xml_sha256,
        },
    )


class EvtxParser(Parser):
    name = "python-evtx"
    version = "2"
    extensions = (".evtx",)

    def parse(self, path: Path):
        try:
            from Evtx.Evtx import Evtx
        except ImportError as exc:
            raise ValueError(
                "parser EVTX opcional ausente; instale pensieve-timeline[evtx]"
            ) from exc

        with Evtx(str(path)) as log:
            for index, record in enumerate(log.records(), start=1):
                try:
                    xml_text = record.xml()
                except Exception as exc:
                    raise ValueError(
                        f"{path}: EVTX record {index}: python-evtx XML extraction failed"
                    ) from exc

                yield parse_evtx_xml(
                    xml_text,
                    source_path=str(path),
                    fallback_index=index,
                )
