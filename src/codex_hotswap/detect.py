from __future__ import annotations

from dataclasses import dataclass
import re


DEFAULT_TRIGGER_PATTERNS = [
    r"\brate[_ -]?limit\b",
    r"\bquota\b",
    r"\btoo many requests\b",
    r"\b429\b",
    r"\bcapacity\b",
    r"\bprovider error\b",
    r"\bmodel unavailable\b",
]


@dataclass(slots=True)
class DetectionResult:
    triggered: bool
    pattern: str | None = None


class TriggerDetector:
    def __init__(self, patterns: list[str] | None = None) -> None:
        self._patterns = [re.compile(pattern, re.IGNORECASE) for pattern in (patterns or DEFAULT_TRIGGER_PATTERNS)]

    def detect(self, text: str) -> DetectionResult:
        for pattern in self._patterns:
            if pattern.search(text):
                return DetectionResult(triggered=True, pattern=pattern.pattern)
        return DetectionResult(triggered=False, pattern=None)

