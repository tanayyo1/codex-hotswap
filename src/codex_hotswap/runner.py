from __future__ import annotations

from dataclasses import dataclass
import errno
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
        command = self.build_command(target, user_args)
        env = self.build_env(target)
        print(f"codex-hotswap: using target '{target.name}'")
        if target.codex_home:
            print(f"codex-hotswap: CODEX_HOME={target.codex_home}")
        output, exit_code = self._spawn_pty(command, env)
        decoded_output = output.decode("utf-8", errors="replace")
        detection = self.detector.detect(decoded_output)
        return RunOutcome(
            exit_code=exit_code,
            triggered=exit_code != 0 and detection.triggered,
            trigger_pattern=detection.pattern,
        )

    def build_command(self, target: Target, user_args: list[str]) -> list[str]:
        return ["codex", *target.codex_args(), *user_args]

    def build_env(self, target: Target) -> dict[str, str]:
        env = os.environ.copy()
        env.update(target.env_overrides())
        return env

    def _spawn_pty(self, command: list[str], env: dict[str, str]) -> tuple[bytearray, int]:
        output = bytearray()
        pid, master_fd = pty.fork()
        if pid == 0:
            os.execvpe(command[0], command, env)

        try:
            while True:
                try:
                    data = os.read(master_fd, 1024)
                    if not data:
                        break
                    output.extend(data)
                    os.write(1, data)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
        finally:
            os.close(master_fd)

        _, status = os.waitpid(pid, 0)
        return output, os.waitstatus_to_exitcode(status)


def format_target_line(config: Config, state_store: StateStore, target_name: str) -> str:
    state = state_store.load()
    current_name = state_store.ensure_current_target(config, state)
    marker = "->" if target_name == current_name else "  "
    exhausted = state.exhausted_targets.get(target_name)
    suffix = ""
    if exhausted:
        suffix = f" [exhausted: {exhausted.reason}]"
    target = config.get_target(target_name)
    if target.codex_home:
        suffix += f" [CODEX_HOME={target.codex_home}]"
    if not target.active:
        suffix += " [inactive]"
    return f"{marker} {target_name}{suffix}"
