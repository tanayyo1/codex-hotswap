from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
import json

from .config import Config


DEFAULT_STATE_PATH = Path.home() / ".local" / "state" / "codex-hotswap" / "state.json"


@dataclass(slots=True)
class ExhaustedTarget:
    reason: str
    exhausted_at: str


@dataclass(slots=True)
class State:
    current_target: str | None = None
    exhausted_targets: dict[str, ExhaustedTarget] = field(default_factory=dict)


class StateStore:
    def __init__(self, path: Path = DEFAULT_STATE_PATH) -> None:
        self.path = path

    def load(self) -> State:
        if not self.path.exists():
            return State()

        raw = json.loads(self.path.read_text())
        exhausted = {
            name: ExhaustedTarget(**value)
            for name, value in raw.get("exhausted_targets", {}).items()
            if isinstance(value, dict)
        }
        current_target = raw.get("current_target")
        if current_target is not None and not isinstance(current_target, str):
            current_target = None
        return State(current_target=current_target, exhausted_targets=exhausted)

    def save(self, state: State) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "current_target": state.current_target,
            "exhausted_targets": {
                name: {
                    "reason": item.reason,
                    "exhausted_at": item.exhausted_at,
                }
                for name, item in state.exhausted_targets.items()
            },
        }
        self.path.write_text(json.dumps(data, indent=2) + "\n")

    def ensure_current_target(self, config: Config, state: State) -> str:
        active_names = {target.name for target in config.active_targets()}
        if state.current_target in active_names:
            return state.current_target

        for target in config.targets:
            if target.active:
                state.current_target = target.name
                self.save(state)
                return target.name
        raise ValueError("No active targets available")

    def ensure_runnable_target(self, config: Config, state: State) -> str:
        current = self.ensure_current_target(config, state)
        if current not in state.exhausted_targets:
            return current

        next_name = self.next_available_target(config, state, start_from=current)
        if next_name is None:
            raise ValueError("No runnable targets available")
        state.current_target = next_name
        self.save(state)
        return next_name

    def mark_exhausted(self, state: State, target: str, reason: str) -> None:
        state.exhausted_targets[target] = ExhaustedTarget(
            reason=reason,
            exhausted_at=datetime.now(UTC).isoformat(),
        )
        self.save(state)

    def reset(self, state: State, target: str | None = None) -> None:
        if target is None:
            state.exhausted_targets.clear()
        else:
            state.exhausted_targets.pop(target, None)
        self.save(state)

    def next_available_target(self, config: Config, state: State, start_from: str | None = None) -> str | None:
        active_targets = [target.name for target in config.targets if target.active]
        available_targets = [name for name in active_targets if name not in state.exhausted_targets]
        if not available_targets:
            return None

        current = start_from or self.ensure_current_target(config, state)
        if current not in active_targets:
            return available_targets[0]

        ordered = active_targets
        start_index = ordered.index(current)
        for step in range(1, len(ordered) + 1):
            candidate = ordered[(start_index + step) % len(ordered)]
            if candidate in state.exhausted_targets:
                continue
            return candidate
        return None

    def set_current_target(self, state: State, target: str) -> None:
        state.current_target = target
        self.save(state)
