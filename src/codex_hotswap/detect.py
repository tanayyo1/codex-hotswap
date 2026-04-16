from __future__ import annotations

from dataclasses import dataclass
import re


LIVE_TRIGGER_PATTERNS = [
    r"\byou(?:'|’)ve hit your usage limit\b",
    r"\brate(?: |_)?limit(?: exceeded| reached)?\b",
    r"\btoo many requests\b",
    r"\bquota exceeded\b",
    r"\b429\b",
    r"\bmodel unavailable\b",
]

EXIT_TRIGGER_PATTERNS = [
    *LIVE_TRIGGER_PATTERNS,
    r"\bprovider returned an error\b",
    r"\bupstream provider error\b",
]


@dataclass(slots=True)
class DetectionResult:
    triggered: bool
    pattern: str | None = None


class TriggerDetector:
    def __init__(
        self,
        *,
        live_patterns: list[str] | None = None,
        exit_patterns: list[str] | None = None,
        live_window_chars: int = 4000,
    ) -> None:
        self._live_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in (live_patterns or LIVE_TRIGGER_PATTERNS)]
        self._exit_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in (exit_patterns or EXIT_TRIGGER_PATTERNS)]
        self._live_window_chars = live_window_chars

    def detect_live(self, text: str) -> DetectionResult:
        window = text[-self._live_window_chars :]
        return self._detect(window, self._live_patterns)

    def detect_exit(self, text: str) -> DetectionResult:
        return self._detect(text, self._exit_patterns)

    def detect(self, text: str) -> DetectionResult:
        return self.detect_exit(text)

    def _detect(self, text: str, patterns: list[re.Pattern[str]]) -> DetectionResult:
        for pattern in patterns:
            if pattern.search(text):
                return DetectionResult(triggered=True, pattern=pattern.pattern)
        return DetectionResult(triggered=False, pattern=None)
