"""Capability diagnostics without inspecting case evidence."""

import importlib.util, platform, sqlite3, sys
from pensieve_timeline import __version__

def _available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:
        return False

def diagnose() -> dict[str, object]:
    with sqlite3.connect(":memory:") as connection:
        sqlite_ok = connection.execute("SELECT 1").fetchone() == (1,)
    python_ok = sys.version_info >= (3, 10)
    return {
        "project": "The Pensieve Project", "version": __version__,
        "python": platform.python_version(), "platform": platform.system(),
        "sqlite": sqlite3.sqlite_version, "python_ok": python_ok, "sqlite_ok": sqlite_ok,
        "optional_capabilities": {
            "evtx": _available("Evtx"), "registry": _available("regipy"),
            "dissect": _available("dissect.target"), "gliner": _available("gliner"),
            "qwen_transformers": _available("transformers"), "ml": _available("sklearn"),
            "forensic_artifacts_yaml": _available("yaml"),
        },
        "ok": python_ok and sqlite_ok, "stage": "v0.3-dfir-osint-reasoning",
    }
