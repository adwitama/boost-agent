"""Read-only fixture repositories; production connectors are intentionally absent."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


class FixtureRepository:
    def __init__(self, path: Path): self.path = path
    def rows(self) -> list[dict[str, Any]]:
        with self.path.open(encoding="utf-8") as source: return json.load(source)


class MockAdsRepository(FixtureRepository): pass
class MockBookRepository(FixtureRepository): pass
