from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable
from pensieve_timeline.model import ForensicEvent

class Parser(ABC):
    name="base"; version="1"; extensions=()
    def supports(self, path: Path) -> bool: return path.suffix.lower() in self.extensions
    @abstractmethod
    def parse(self, path: Path) -> Iterable[ForensicEvent]: raise NotImplementedError

class ParserRegistry:
    def __init__(self, parsers=()): self._parsers=list(parsers)
    def resolve(self, path: Path) -> Parser:
        for parser in self._parsers:
            if parser.supports(path): return parser
        supported=sorted({x for p in self._parsers for x in p.extensions})
        raise ValueError(f"formato não suportado: {path.suffix or '<sem extensão>'}; suportados: {', '.join(supported)}")
