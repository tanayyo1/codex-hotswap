from __future__ import annotations

from dataclasses import dataclass
import os
import pty
import time

from .config import Config, Target
from .detect import TriggerDetector
from .state import StateStore


@dataclass(slots=True)
class RunOutcome:
    exit_code: int
    triggered: bool
    trigger_pattern: str | None


class CodexRunner:
    def __init__(self, config: Config, state_store: StateStore, detector: TriggerDetector | None = None) -> None:
        self.config = config
        self.state_store = state_store
        self.detector = detector or TriggerDetector()

    def run(self, user_args: list[str]) -> int:
        state = self.state_store.load()
        try:
            current_name = self.state_store.ensure_runnable_target(self.config, state)
        except ValueError:
            print("codex-hotswap: no runnable targets available")
            return 1
        target = self.config.get_target(current_name)

        swaps = 0
        current_args = list(user_args)
        while True:
            outcome = self._invoke(target, current_args)
            if not outcome.triggered:
                return outcome.exit_code

            self.state_store.mark_exhausted(state, target.name, f"triggered by {outcome.trigger_pattern}")
            next_name = self.state_store.next_available_target(self.config, state, start_from=target.name)
            if next_name is None:
                print("codex-hotswap: no non-exhausted targets remain")
                return 1

            swaps += 1
            if swaps > self.config.settings.max_swaps:
                print(f"codex-hotswap: reached max swap attempts ({self.config.settings.max_swaps})")
                return 1

            self.state_store.set_current_target(state, next_name)
            target = self.config.get_target(next_name)
            print(f"codex-hotswap: trigger matched; rotating to '{next_name}'")
            time.sleep(self.config.settings.swap_delay_seconds)
            current_args = ["resume", "--last"]

    def _invoke(self, target: Target, user_args: list[str]) -> RunOutcome:
        command = ["codex", *target.codex_args(), *user_args]
        print(f"codex-hotswap: using target '{target.name}'")
        output = bytearray()

        def read(fd: int) -> bytes:
            data = os.read(fd, 1024)
            output.extend(data)
            return data

        status = pty.spawn(command, master_read=read)
        exit_code = os.waitstatus_to_exitcode(status)
        decoded_output = output.decode("utf-8", errors="replace")
        detection = self.detector.detect(decoded_output)
        return RunOutcome(
            exit_code=exit_code,
            triggered=exit_code != 0 and detection.triggered,
            trigger_pattern=detection.pattern,
        )


def format_target_line(config: Config, state_store: StateStore, target_name: str) -> str:
    state = state_store.load()
    current_name = state_store.ensure_current_target(config, state)
    marker = "->" if target_name == current_name else "  "
    exhausted = state.exhausted_targets.get(target_name)
    suffix = ""
    if exhausted:
        suffix = f" [exhausted: {exhausted.reason}]"
    target = config.get_target(target_name)
    if not target.active:
        suffix += " [inactive]"
    return f"{marker} {target_name}{suffix}"
