from __future__ import annotations

from dataclasses import dataclass
import errno
import fcntl
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import signal
import struct
import sys
import tempfile
import termios
import subprocess
import time
import tty

from .auth import AuthManager
from .config import Config, ConfigError, Target
from .detect import TriggerDetector
from .state import StateStore

RUNTIME_LOCK_FILENAME = ".codex-hotswap.lock"


@dataclass(slots=True)
class RunOutcome:
    exit_code: int
    triggered: bool
    trigger_pattern: str | None


@dataclass(slots=True)
class InteractiveResult:
    output: bytearray
    exit_code: int
    live_trigger_pattern: str | None = None


class SharedHomeSessionLock:
    def __init__(self, shared_home: Path, initial_target: str) -> None:
        self.shared_home = shared_home
        self.current_target = initial_target
        self.lock_path = shared_home / RUNTIME_LOCK_FILENAME
        self._handle = None

    def __enter__(self) -> "SharedHomeSessionLock":
        self.shared_home.mkdir(parents=True, exist_ok=True)
        self._handle = self.lock_path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._handle.close()
            self._handle = None
            raise ConfigError(
                "another codex-hotswap session is already using the shared CODEX_HOME; "
                "finish that session first or use a different shared_codex_home"
            ) from exc
        self.update_target(self.current_target)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            self._handle.truncate()
            self._handle.flush()
            os.fsync(self._handle.fileno())
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None

    def update_target(self, target: str) -> None:
        self.current_target = target
        if self._handle is None:
            return
        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(f"pid={os.getpid()}\ntarget={target}\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())


class CodexRunner:
    def __init__(
        self,
        config: Config,
        state_store: StateStore,
        detector: TriggerDetector | None = None,
        real_codex_binary: str | None = None,
    ) -> None:
        self.config = config
        self.state_store = state_store
        self.detector = detector or TriggerDetector()
        self.auth_manager = AuthManager(config)
        self.real_codex_binary = real_codex_binary

    def run(self, user_args: list[str]) -> int:
        try:
            state = self.state_store.load()
            current_name = self.state_store.ensure_runnable_target(self.config, state)
        except ConfigError as exc:
            print(f"codex-hotswap: {exc}")
            return 1
        except ValueError:
            print("codex-hotswap: no runnable targets available")
            return 1
        try:
            with self._acquire_runtime_lock(current_name) as runtime_lock:
                target = self.config.get_target(current_name)
                swaps = 0
                current_args = list(user_args)
                while True:
                    outcome = self._invoke(target, current_args)
                    if not outcome.triggered:
                        return outcome.exit_code

                    self.state_store.mark_exhausted(
                        state,
                        target.name,
                        f"triggered by {outcome.trigger_pattern}",
                        cooldown_minutes=self.config.settings.default_cooldown_minutes,
                    )
                    next_name = self.state_store.next_available_target(self.config, state, start_from=target.name)
                    if next_name is None:
                        print("codex-hotswap: no non-exhausted targets remain")
                        return 1

                    swaps += 1
                    if swaps > self.config.settings.max_swaps:
                        print(f"codex-hotswap: reached max swap attempts ({self.config.settings.max_swaps})")
                        return 1

                    self.state_store.set_current_target(state, next_name)
                    runtime_lock.update_target(next_name)
                    target = self.config.get_target(next_name)
                    print(f"codex-hotswap: trigger matched; rotating to '{next_name}'")
                    time.sleep(self.config.settings.swap_delay_seconds)
                    current_args = ["resume", "--last"]
        except ConfigError as exc:
            print(f"codex-hotswap: {exc}")
            return 1

    def login(self, target: Target, login_args: list[str], *, relogin: bool = False) -> int:
        if not relogin:
            logged_in, status_text = self.login_status(target)
            if logged_in:
                print(f"codex-hotswap: target '{target.name}' is already logged in")
                if status_text:
                    print(f"codex-hotswap: {status_text}")
                print("codex-hotswap: use --relogin if you want to run codex login again")
                return 0
        print(f"codex-hotswap: logging into target '{target.name}'")
        if target.codex_home:
            print(f"codex-hotswap: auth vault={target.expanded_codex_home()}")
        command = self.build_command(target, ["login", *login_args])
        env = self.build_login_env(target)
        result = self._spawn_interactive(command, env)
        return result.exit_code

    def login_status(self, target: Target) -> tuple[bool, str]:
        command = self.build_command(target, ["login", "status"])
        env = self.build_login_env(target)
        try:
            result = subprocess.run(command, env=env, capture_output=True, text=True)
        except FileNotFoundError:
            return False, "codex binary not found in PATH"
        except OSError as exc:
            return False, str(exc)
        text = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part and part.strip())
        if result.returncode == 0 and "logged in" in text.lower():
            return True, text
        return False, text

    def _invoke(self, target: Target, user_args: list[str]) -> RunOutcome:
        self.auth_manager.activate(target)
        result = self._run_runtime_passthrough(target, user_args, announce=True)
        if result.live_trigger_pattern is not None:
            return RunOutcome(
                exit_code=result.exit_code,
                triggered=True,
                trigger_pattern=result.live_trigger_pattern,
            )

        decoded_output = result.output.decode("utf-8", errors="replace")
        detection = self.detector.detect_exit(decoded_output)
        return RunOutcome(
            exit_code=result.exit_code,
            triggered=result.exit_code != 0 and detection.triggered,
            trigger_pattern=detection.pattern,
        )

    def _run_runtime_passthrough(
        self,
        target: Target,
        user_args: list[str],
        *,
        announce: bool = False,
    ) -> InteractiveResult:
        command = self.build_command(target, user_args)
        env = self.build_runtime_env()
        if announce:
            print(f"codex-hotswap: using target '{target.name}'")
            print(f"codex-hotswap: shared CODEX_HOME={self.config.shared_codex_home_path()}")
            if target.codex_home:
                print(f"codex-hotswap: auth vault={target.expanded_codex_home()}")
        return self._spawn_interactive(command, env)

    def build_command(self, target: Target, user_args: list[str]) -> list[str]:
        return [self.codex_binary(), *target.codex_args(), *user_args]

    def codex_binary(self) -> str:
        if self.real_codex_binary:
            return self.real_codex_binary

        resolved = shutil.which("codex")
        if resolved is None:
            return "codex"

        shim_real = self._real_binary_from_shim(Path(resolved))
        return shim_real or resolved

    def _real_binary_from_shim(self, path: Path) -> str | None:
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            return None
        if "# codex-hotswap shim" not in text:
            return None
        for line in text.splitlines():
            if line.startswith("export CODEX_HOTSWAP_REAL_BIN="):
                value = line.split("=", 1)[1].strip().strip('"')
                if value:
                    return value
        return None

    def build_runtime_env(self) -> dict[str, str]:
        env = os.environ.copy()
        shared_home = self.config.shared_codex_home_path()
        env["CODEX_HOME"] = str(shared_home)
        os.makedirs(shared_home, exist_ok=True)
        return env

    def build_login_env(self, target: Target) -> dict[str, str]:
        env = os.environ.copy()
        env.update(target.env_overrides())
        codex_home = env.get("CODEX_HOME")
        if codex_home:
            os.makedirs(codex_home, exist_ok=True)
        return env

    def runtime_lock_path(self) -> Path:
        return self.config.shared_codex_home_path() / RUNTIME_LOCK_FILENAME

    def _acquire_runtime_lock(self, target_name: str) -> SharedHomeSessionLock:
        return SharedHomeSessionLock(self.config.shared_codex_home_path(), target_name)

    def _spawn_interactive(self, command: list[str], env: dict[str, str]) -> InteractiveResult:
        if self._should_use_script():
            return self._spawn_with_script(command, env)
        return self._spawn_pty(command, env)

    def _should_use_script(self) -> bool:
        return (
            sys.platform.startswith("linux")
            and shutil.which("script") is not None
            and os.isatty(sys.stdin.fileno())
            and os.isatty(sys.stdout.fileno())
        )

    def _spawn_with_script(self, command: list[str], env: dict[str, str]) -> InteractiveResult:
        with tempfile.NamedTemporaryFile(prefix="codex-hotswap-", delete=False) as transcript_file:
            transcript_path = transcript_file.name

        try:
            process = subprocess.Popen(
                ["script", "-qefc", shlex.join(command), transcript_path],
                env=env,
                start_new_session=True,
            )
            transcript = bytearray()
            offset = 0
            live_trigger_pattern = None
            sent_interrupt = False

            while True:
                if os.path.exists(transcript_path):
                    data = self._read_appended_bytes(Path(transcript_path), offset)
                    if data:
                        offset += len(data)
                        transcript.extend(data)
                        if live_trigger_pattern is None:
                            detection = self.detector.detect_live(transcript.decode("utf-8", errors="replace"))
                            if detection.triggered:
                                live_trigger_pattern = detection.pattern
                                sent_interrupt = self._signal_process_group(process.pid, signal.SIGINT)

                returncode = process.poll()
                if returncode is not None:
                    if os.path.exists(transcript_path):
                        data = self._read_appended_bytes(Path(transcript_path), offset)
                        if data:
                            transcript.extend(data)
                    return InteractiveResult(
                        output=transcript,
                        exit_code=returncode,
                        live_trigger_pattern=live_trigger_pattern,
                    )

                if live_trigger_pattern is not None and not sent_interrupt:
                    sent_interrupt = self._signal_process_group(process.pid, signal.SIGINT)
                time.sleep(0.1)
        finally:
            try:
                os.remove(transcript_path)
            except FileNotFoundError:
                pass

    def _spawn_pty(self, command: list[str], env: dict[str, str]) -> InteractiveResult:
        output = bytearray()
        pid, master_fd = pty.fork()
        if pid == 0:
            os.execvpe(command[0], command, env)

        stdin_fd = sys.stdin.fileno()
        stdout_fd = sys.stdout.fileno()
        old_tty_settings = None
        previous_winch_handler = None
        live_trigger_pattern = None
        interrupt_sent_at = None

        def sync_winsize(*_: object) -> None:
            try:
                packed = fcntl.ioctl(stdin_fd, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0))
                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, packed)
            except OSError:
                pass

        if os.isatty(stdin_fd):
            old_tty_settings = termios.tcgetattr(stdin_fd)
            tty.setraw(stdin_fd)
            sync_winsize()
            previous_winch_handler = signal.getsignal(signal.SIGWINCH)
            signal.signal(signal.SIGWINCH, sync_winsize)

        try:
            stdin_open = True
            exit_status = None
            while True:
                read_fds = [master_fd]
                if stdin_open:
                    read_fds.append(stdin_fd)

                ready, _, _ = select.select(read_fds, [], [], 0.1)

                if master_fd in ready:
                    try:
                        data = os.read(master_fd, 1024)
                        if not data:
                            break
                        output.extend(data)
                        os.write(stdout_fd, data)
                    except OSError as exc:
                        if exc.errno == errno.EIO:
                            break
                        raise

                    if live_trigger_pattern is None:
                        detection = self.detector.detect_live(output.decode("utf-8", errors="replace"))
                        if detection.triggered:
                            live_trigger_pattern = detection.pattern
                            if self._signal_process(pid, signal.SIGINT):
                                interrupt_sent_at = time.time()

                if stdin_open and stdin_fd in ready:
                    try:
                        user_input = os.read(stdin_fd, 1024)
                    except OSError:
                        stdin_open = False
                    else:
                        if not user_input:
                            stdin_open = False
                        else:
                            os.write(master_fd, user_input)

                waited_pid, status = os.waitpid(pid, os.WNOHANG)
                if waited_pid == pid:
                    exit_status = status
                    break

                if interrupt_sent_at is not None and time.time() - interrupt_sent_at > 1:
                    self._signal_process(pid, signal.SIGTERM)
                    interrupt_sent_at = None
        finally:
            if previous_winch_handler is not None:
                signal.signal(signal.SIGWINCH, previous_winch_handler)
            if old_tty_settings is not None:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_tty_settings)
            os.close(master_fd)

        if exit_status is None:
            _, exit_status = os.waitpid(pid, 0)
        return InteractiveResult(
            output=output,
            exit_code=os.waitstatus_to_exitcode(exit_status),
            live_trigger_pattern=live_trigger_pattern,
        )

    def _read_appended_bytes(self, path: Path, offset: int) -> bytes:
        with path.open("rb") as handle:
            handle.seek(offset)
            return handle.read()

    def _signal_process_group(self, pid: int, sig: signal.Signals) -> bool:
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            return False
        except OSError as exc:
            if exc.errno == errno.ESRCH:
                return False
            raise
        return True

    def _signal_process(self, pid: int, sig: signal.Signals) -> bool:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return False
        except OSError as exc:
            if exc.errno == errno.ESRCH:
                return False
            raise
        return True


def format_target_line(config: Config, state_store: StateStore, target_name: str, state=None) -> str:
    resolved_state = state or state_store.load()
    current_name = state_store.ensure_current_target(config, resolved_state)
    marker = "->" if target_name == current_name else "  "
    exhausted = resolved_state.exhausted_targets.get(target_name)
    suffix = ""
    if exhausted:
        suffix = f" [exhausted: {exhausted.reason}]"
        if exhausted.available_at:
            suffix += f" [available_at={exhausted.available_at}]"
    target = config.get_target(target_name)
    if target.codex_home:
        suffix += f" [auth_vault={target.codex_home}]"
    if not target.active:
        suffix += " [inactive]"
    return f"{marker} {target_name}{suffix}"
