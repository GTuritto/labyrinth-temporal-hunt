from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Iterable, List, Tuple

from loguru import logger
from rich.console import Console
from rich.table import Table


@dataclass
class MemoryItem:
    role: str
    content: str


@dataclass
class MemoryManager:
    max_items: int = 200
    buffer: Deque[MemoryItem] = field(default_factory=deque)

    def add(self, role: str, content: str) -> None:
        if len(self.buffer) >= self.max_items:
            removed = self.buffer.popleft()
            logger.debug(f"Memory overflow; dropping oldest: {removed.role} -> {removed.content[:40]}")
        self.buffer.append(MemoryItem(role=role, content=content))

    def extend(self, items: Iterable[Tuple[str, str]]) -> None:
        for role, content in items:
            self.add(role, content)

    def get_history(self) -> List[Tuple[str, str]]:
        return [(m.role, m.content) for m in list(self.buffer)]

    def render(self) -> None:
        console = Console()
        table = Table(title="Conversation Memory")
        table.add_column("Role")
        table.add_column("Content")
        for m in list(self.buffer)[-20:]:
            table.add_row(m.role, (m.content[:120] + "...") if len(m.content) > 120 else m.content)
        console.print(table)
