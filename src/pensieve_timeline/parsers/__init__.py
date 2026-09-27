"""Parser registries for the lightweight core and optional forensic backends."""

from pensieve_timeline.parsers.base import ParserRegistry
from pensieve_timeline.parsers.tabular import DelimitedParser, JsonlParser


def default_registry() -> ParserRegistry:
    """Return the dependency-free parser registry used by normal CLI ingestion."""
    return ParserRegistry([DelimitedParser(), JsonlParser()])


def extended_registry() -> ParserRegistry:
    """Return parsers that require optional forensic dependencies or corpus validation."""
    from pensieve_timeline.adapters.dissect_target import DissectTargetParser
    from pensieve_timeline.parsers.evtx import EvtxParser
    from pensieve_timeline.parsers.registry import RegistryHiveParser

    return ParserRegistry(
        [
            DelimitedParser(),
            JsonlParser(),
            EvtxParser(),
            RegistryHiveParser(),
            DissectTargetParser(),
        ]
    )


__all__ = [
    "ParserRegistry",
    "DelimitedParser",
    "JsonlParser",
    "default_registry",
    "extended_registry",
]
