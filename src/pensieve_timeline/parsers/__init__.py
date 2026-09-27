from pensieve_timeline.adapters.dissect_target import DissectTargetParser
from pensieve_timeline.parsers.base import ParserRegistry
from pensieve_timeline.parsers.evtx import EvtxParser
from pensieve_timeline.parsers.registry import RegistryHiveParser
from pensieve_timeline.parsers.tabular import DelimitedParser, JsonlParser

def default_registry():
    return ParserRegistry([DelimitedParser(),JsonlParser(),EvtxParser(),RegistryHiveParser(),DissectTargetParser()])
