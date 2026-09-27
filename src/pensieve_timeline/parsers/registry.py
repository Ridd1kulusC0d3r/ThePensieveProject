"""Optional standalone Windows Registry hive parser using regipy."""

from dataclasses import asdict, is_dataclass
from pensieve_timeline.model import ForensicEvent, parse_timestamp
from pensieve_timeline.parsers.base import Parser

class RegistryHiveParser(Parser):
    name = "regipy"
    extensions = (".dat", ".hiv", ".hive", ".regf")

    def supports(self, path):
        if not path.is_file():
            return False
        try:
            with path.open("rb") as handle:
                return handle.read(4) == b"regf"
        except OSError:
            return False

    def parse(self, path):
        try:
            from regipy.registry import RegistryHive
        except ImportError as exc:
            raise ValueError("regipy opcional ausente; instale pensieve-timeline[registry]") from exc
        hive = RegistryHive(str(path))
        hint = "amcache" if "amcache" in path.name.casefold() else "registry"
        for entry in hive.recurse_subkeys(as_json=True):
            row = asdict(entry) if is_dataclass(entry) else dict(entry) if isinstance(entry, dict) else {}
            if not row.get("timestamp"):
                continue
            ts, assumption = parse_timestamp(str(row["timestamp"]))
            key = str(row.get("path") or "/")
            normalized = key.replace("/", "\\").casefold()
            tags = []
            if normalized.endswith("\\run") or normalized.endswith("\\runonce"):
                tags.append("registry-autorun")
            if "\\services\\" in normalized:
                tags.append("registry-service")
            yield ForensicEvent(
                ts, "Windows Registry", hint, f"Registry key modified: {key}",
                event_type="registry_key_modified",
                record_locator=f"key:{key}",
                source_path=str(path),
                parser=self.name,
                parser_version="1",
                time_assumption=assumption,
                tags=tags,
                raw={"key": key, "values": row.get("values") or [], "values_count": row.get("values_count")},
            )
