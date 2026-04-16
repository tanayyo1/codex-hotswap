from __future__ import annotations

from pathlib import Path
import argparse
from dataclasses import replace
import fcntl
import json
import os
import shutil
import sys

from . import __version__
from .auth import ACTIVE_TARGET_METADATA
from .config import Config, ConfigError, DEFAULT_CONFIG_PATH, Settings, Target, load_config, save_config, write_default_config
from .runner import CodexRunner, RUNTIME_LOCK_FILENAME, format_target_line
from .state import DEFAULT_STATE_PATH, StateStore


def build_parser(argv0: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=argv0)
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config.toml")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH, help="Path to state.json")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config.toml")
    common.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH, help="Path to state.json")

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Write a starter config", parents=[common])
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing config")

    setup_parser = subparsers.add_parser("setup", help="Bootstrap a multi-account config", parents=[common])
    setup_parser.add_argument("--accounts", help="Comma-separated target names, e.g. main,work,backup")
    setup_parser.add_argument("--count", type=int, help="Create numbered targets when --accounts is not provided")
    setup_parser.add_argument("--prefix", default="acc", help="Name prefix for generated targets with --count")
    setup_parser.add_argument(
        "--auth-home-prefix",
        dest="auth_home_prefix",
        default="~/.codex-",
        help="Prefix used to generate per-account auth vault paths",
    )
    setup_parser.add_argument(
        "--codex-home-prefix",
        dest="auth_home_prefix",
        help=argparse.SUPPRESS,
    )
    setup_parser.add_argument("--profile", help="Optional profile to assign to generated targets")
    setup_parser.add_argument("--max-swaps", type=int, default=3, help="max_swaps setting for generated config")
    setup_parser.add_argument("--swap-delay-seconds", type=float, default=1.5, help="swap_delay_seconds setting")
    setup_parser.add_argument("--cooldown-minutes", type=int, default=240, help="default_cooldown_minutes setting")
    setup_parser.add_argument("--replace-targets", action="store_true", help="Replace existing targets instead of appending")
    setup_parser.add_argument("--login", action="store_true", help="Run codex login for each created target after setup")
    setup_parser.add_argument("--login-arg", action="append", default=[], help="Additional argument to pass to each codex login command when using --login")
    setup_parser.add_argument("--device-auth", action="store_true", help="Use codex login --device-auth for each target when using --login")
    setup_parser.add_argument("--install-shim", action="store_true", help="Install the codex shim after setup")
    setup_parser.add_argument("--shim-path", type=Path, default=Path.home() / ".local" / "bin" / "codex")
    setup_parser.add_argument("--shim-force", action="store_true", help="Overwrite an existing codex shim when using --install-shim")
    setup_parser.add_argument("--force", action="store_true", help="Allow creating config if missing and replacing generated setup safely")

    subparsers.add_parser("list", help="List configured targets", parents=[common])
    subparsers.add_parser("status", help="Show configured targets and current state", parents=[common])
    subparsers.add_parser("current", help="Print the current target", parents=[common])

    login_parser = subparsers.add_parser("login", help="Run codex login for a target", parents=[common])
    login_parser.add_argument("target")
    login_parser.add_argument("--relogin", action="store_true", help="Run login even if the target already appears authenticated")
    login_parser.add_argument("args", nargs=argparse.REMAINDER)

    add_target_parser = subparsers.add_parser("add-target", help="Add a target to config", parents=[common])
    add_target_parser.add_argument("name")
    add_target_parser.add_argument("--codex-home")
    add_target_parser.add_argument("--profile")
    add_target_parser.add_argument("--model")
    add_target_parser.add_argument("--oss", action="store_true")
    add_target_parser.add_argument("--local-provider")
    add_target_parser.add_argument("--config-override", action="append", default=[])
    add_target_parser.add_argument("--extra-arg", action="append", default=[])
    add_target_parser.add_argument("--inactive", action="store_true")
    add_target_parser.add_argument("--note")

    remove_target_parser = subparsers.add_parser("remove-target", help="Remove a target from config", parents=[common])
    remove_target_parser.add_argument("target")

    use_parser = subparsers.add_parser("use", help="Set the active target", parents=[common])
    use_parser.add_argument("target")

    next_parser = subparsers.add_parser("next", help="Rotate to the next available target", parents=[common])
    next_parser.add_argument("--print-only", action="store_true", help="Do not update state")

    exhaust_parser = subparsers.add_parser("exhaust", help="Mark a target as exhausted", parents=[common])
    exhaust_parser.add_argument("target")
    exhaust_parser.add_argument("--reason", default="manual")
    exhaust_parser.add_argument("--cooldown-minutes", type=int)

    reset_parser = subparsers.add_parser("reset", help="Clear exhaustion markers", parents=[common])
    reset_parser.add_argument("target", nargs="?")

    run_parser = subparsers.add_parser("run", help="Run codex through the hotswap wrapper", parents=[common])
    run_parser.add_argument("args", nargs=argparse.REMAINDER)

    install_shim_parser = subparsers.add_parser("install-shim", help="Install a codex shim that routes through codex-hotswap", parents=[common])
    install_shim_parser.add_argument("--path", type=Path, default=Path.home() / ".local" / "bin" / "codex")
    install_shim_parser.add_argument("--real-bin", type=Path, help="Explicit path to the real codex binary")
    install_shim_parser.add_argument("--force", action="store_true", help="Overwrite an existing shim at the target path")

    uninstall_shim_parser = subparsers.add_parser("uninstall-shim", help="Remove the installed codex shim", parents=[common])
    uninstall_shim_parser.add_argument("--path", type=Path, default=Path.home() / ".local" / "bin" / "codex")

    doctor_parser = subparsers.add_parser("doctor", help="Check config, auth vaults, shared home, and shim status", parents=[common])
    doctor_parser.add_argument("--shim-path", type=Path, default=Path.home() / ".local" / "bin" / "codex")
    doctor_parser.add_argument("--skip-login-status", action="store_true", help="Skip codex login status checks for each target")

    return parser


def main() -> int:
    argv0 = Path(sys.argv[0]).name
    if argv0 == "codex-hot":
        return _run_wrapper(sys.argv[1:])

    parser = build_parser(argv0)
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "init":
        try:
            path = write_default_config(args.config_path, force=args.force)
        except ConfigError as exc:
            print(f"codex-hotswap: {exc}", file=sys.stderr)
            return 1
        print(path)
        return 0

    if args.command == "setup":
        try:
            _validate_setup_args(args)
            target_names = _resolve_setup_target_names(args.accounts, args.count, args.prefix)
            config = _load_or_create_setup_config(
                args.config_path,
                max_swaps=args.max_swaps,
                swap_delay_seconds=args.swap_delay_seconds,
                cooldown_minutes=args.cooldown_minutes,
                force=args.force,
            )
            generated_targets = _build_setup_targets(
                target_names=target_names,
                auth_home_prefix=args.auth_home_prefix,
                profile=args.profile,
            )
            config = _merge_setup_targets(config, generated_targets, replace_targets=args.replace_targets)
            save_config(config, args.config_path)

            state_store = StateStore(args.state_path)
            state = state_store.load()
            state_store.set_current_target(state, generated_targets[0].name)

            print(f"codex-hotswap: configured {len(generated_targets)} target(s) in {args.config_path}")
            print(f"codex-hotswap: current target set to {generated_targets[0].name}")
            for target in generated_targets:
                print(f"  - {target.name} -> auth vault {target.codex_home}")

            if args.login:
                login_args = list(args.login_arg)
                if args.device_auth:
                    login_args.append("--device-auth")
                runner = CodexRunner(config=config, state_store=state_store)
                for target in generated_targets:
                    exit_code = runner.login(target, login_args)
                    if exit_code != 0:
                        return exit_code
            if args.install_shim:
                try:
                    path = _install_codex_shim(args.shim_path, force=args.shim_force)
                except ConfigError as exc:
                    print(f"codex-hotswap: {exc}", file=sys.stderr)
                    return 1
                print(f"codex-hotswap: installed shim at {path}")
            return 0
        except ConfigError as exc:
            print(f"codex-hotswap: {exc}", file=sys.stderr)
            return 1

    try:
        config = load_config(args.config_path)
    except ConfigError as exc:
        print(f"codex-hotswap: {exc}", file=sys.stderr)
        return 1

    state_store = StateStore(args.state_path)
    state = state_store.load()

    if args.command in {"list", "status"}:
        for target in config.targets:
            print(format_target_line(config, state_store, target.name))
        return 0

    if args.command == "current":
        current = state_store.ensure_current_target(config, state)
        print(current)
        return 0

    if args.command == "login":
        target = config.get_target(args.target)
        runner = CodexRunner(config=config, state_store=state_store)
        return runner.login(target, _normalize_remainder(args.args), relogin=args.relogin)

    if args.command == "add-target":
        target = Target(
            name=args.name,
            codex_home=args.codex_home,
            profile=args.profile,
            model=args.model,
            oss=args.oss,
            local_provider=args.local_provider,
            config_overrides=args.config_override,
            extra_args=args.extra_arg,
            active=not args.inactive,
            note=args.note,
        )
        updated = config.with_added_target(target)
        save_config(updated, args.config_path)
        print(args.name)
        return 0

    if args.command == "remove-target":
        updated = config.without_target(args.target)
        save_config(updated, args.config_path)
        print(args.target)
        return 0

    if args.command == "use":
        target = config.get_target(args.target)
        if not target.active:
            print(f"codex-hotswap: target is inactive: {args.target}", file=sys.stderr)
            return 1
        state_store.set_current_target(state, args.target)
        print(args.target)
        return 0

    if args.command == "next":
        next_name = state_store.next_available_target(config, state)
        if next_name is None:
            print("codex-hotswap: no non-exhausted targets remain", file=sys.stderr)
            return 1
        if not args.print_only:
            state_store.set_current_target(state, next_name)
        print(next_name)
        return 0

    if args.command == "exhaust":
        config.get_target(args.target)
        state_store.mark_exhausted(state, args.target, args.reason, cooldown_minutes=args.cooldown_minutes)
        print(args.target)
        return 0

    if args.command == "reset":
        if args.target is not None:
            config.get_target(args.target)
        state_store.reset(state, args.target)
        print("ok")
        return 0

    if args.command == "run":
        runner = CodexRunner(config=config, state_store=state_store)
        return runner.run(_normalize_remainder(args.args))

    if args.command == "doctor":
        return _run_doctor(config, state_store, state, shim_path=args.shim_path, skip_login_status=args.skip_login_status)

    if args.command == "install-shim":
        try:
            path = _install_codex_shim(args.path, real_bin=args.real_bin, force=args.force)
        except ConfigError as exc:
            print(f"codex-hotswap: {exc}", file=sys.stderr)
            return 1
        print(path)
        return 0

    if args.command == "uninstall-shim":
        try:
            removed = _uninstall_codex_shim(args.path)
        except ConfigError as exc:
            print(f"codex-hotswap: {exc}", file=sys.stderr)
            return 1
        if removed:
            print(args.path)
        return 0

    parser.print_help()
    return 1


def _run_wrapper(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="codex-hot", add_help=False, allow_abbrev=False)
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config.toml")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH, help="Path to state.json")
    parsed, remainder = parser.parse_known_args(argv)

    try:
        config = load_config(parsed.config_path)
    except ConfigError as exc:
        print(f"codex-hotswap: {exc}", file=sys.stderr)
        return 1

    runner = CodexRunner(config=config, state_store=StateStore(parsed.state_path))
    return runner.run(_normalize_remainder(remainder))


def _normalize_remainder(values: list[str]) -> list[str]:
    if values and values[0] == "--":
        return values[1:]
    return values


def _validate_setup_args(args: argparse.Namespace) -> None:
    if (args.login_arg or args.device_auth) and not args.login:
        raise ConfigError("--login-arg and --device-auth require --login")
    if args.shim_force and not args.install_shim:
        raise ConfigError("--shim-force requires --install-shim")


def _resolve_setup_target_names(accounts: str | None, count: int | None, prefix: str) -> list[str]:
    if accounts:
        names = [item.strip() for item in accounts.split(",") if item.strip()]
        if not names:
            raise ConfigError("--accounts must include at least one name")
        if len(set(names)) != len(names):
            raise ConfigError("--accounts contains duplicate target names")
        return names

    resolved_count = count or 2
    if resolved_count < 1:
        raise ConfigError("--count must be a positive integer")
    if not prefix.strip():
        raise ConfigError("--prefix must be a non-empty string")
    return [f"{prefix}{index}" for index in range(1, resolved_count + 1)]


def _load_or_create_setup_config(
    path: Path,
    *,
    max_swaps: int,
    swap_delay_seconds: float,
    cooldown_minutes: int,
    force: bool,
) -> Config:
    if path.exists():
        config = load_config(path)
        if config.settings.shared_codex_home is None:
            config = Config(
                path=config.path,
                settings=replace(config.settings, shared_codex_home="~/.codex"),
                targets=config.targets,
            )
        return config
    if not force:
        raise ConfigError(f"Config file not found: {path}. Re-run with --force to create it.")
    return Config(
        path=path,
        settings=Settings(
            max_swaps=max_swaps,
            swap_delay_seconds=swap_delay_seconds,
            default_cooldown_minutes=cooldown_minutes,
            shared_codex_home="~/.codex",
        ),
        targets=[],
    )


def _build_setup_targets(
    *,
    target_names: list[str],
    auth_home_prefix: str,
    profile: str,
) -> list[Target]:
    if not auth_home_prefix.strip():
        raise ConfigError("--auth-home-prefix must be a non-empty string")
    return [
        Target(
            name=name,
            codex_home=f"{auth_home_prefix}{name}",
            profile=profile,
            note=f"Configured by setup for {name}",
        )
        for name in target_names
    ]


def _merge_setup_targets(config: Config, generated_targets: list[Target], *, replace_targets: bool) -> Config:
    if replace_targets:
        return Config(path=config.path, settings=config.settings, targets=generated_targets)

    replacements = {target.name: target for target in generated_targets}
    updated_targets: list[Target] = []
    for existing in config.targets:
        replacement = replacements.pop(existing.name, None)
        updated_targets.append(replacement or existing)
    updated_targets.extend(target for target in generated_targets if target.name in replacements)
    return Config(path=config.path, settings=config.settings, targets=updated_targets)


def _install_codex_shim(path: Path, *, real_bin: Path | None = None, force: bool = False) -> Path:
    if real_bin is None:
        real_bin = _resolve_real_codex_binary(path)
    if real_bin is None:
        raise ConfigError("Could not find the real codex binary")

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not force and not _is_codex_shim(path):
            raise ConfigError(f"Shim path already exists: {path}. Re-run with --force to replace it.")
        if path.is_dir():
            raise ConfigError(f"Shim path is a directory: {path}")

    content = _render_codex_shim(real_bin)
    path.write_text(content)
    path.chmod(0o755)
    return path


def _uninstall_codex_shim(path: Path) -> bool:
    if not path.exists():
        return False
    if not _is_codex_shim(path):
        raise ConfigError(f"Refusing to remove non-shim file: {path}")
    path.unlink()
    return True


def _resolve_real_codex_binary(shim_path: Path) -> Path | None:
    if shim_path.exists() and _is_codex_shim(shim_path):
        for line in shim_path.read_text(errors="ignore").splitlines():
            if line.startswith("export CODEX_HOTSWAP_REAL_BIN="):
                value = line.split("=", 1)[1].strip().strip('"')
                if value:
                    return Path(value)
    resolved = shutil.which("codex")
    if resolved is None:
        return None
    resolved_path = Path(resolved)
    if resolved_path == shim_path:
        return None
    return resolved_path


def _is_codex_shim(path: Path) -> bool:
    try:
        return "# codex-hotswap shim" in path.read_text(errors="ignore")
    except (OSError, UnicodeError):
        return False


def _render_codex_shim(real_bin: Path) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "# codex-hotswap shim",
            f'export CODEX_HOTSWAP_REAL_BIN="{real_bin}"',
            'exec codex-hot "$@"',
            "",
        ]
    )


def _run_doctor(
    config: Config,
    state_store: StateStore,
    state,
    *,
    shim_path: Path,
    skip_login_status: bool,
) -> int:
    runner = CodexRunner(config=config, state_store=state_store)
    current_target = state_store.ensure_current_target(config, state)
    issues: list[str] = []

    shared_home = config.shared_codex_home_path()
    print(f"shared home: {shared_home}")
    if shared_home.exists():
        print("shared home status: ok")
    else:
        print("shared home status: missing")
        issues.append("shared home is missing")

    shared_auth = shared_home / "auth.json"
    if shared_auth.exists():
        print("shared auth: present")
    else:
        print("shared auth: missing")
        issues.append("shared auth.json is missing")

    print(f"current target: {current_target}")

    resolved_codex = shutil.which("codex")
    print(f"codex on PATH: {resolved_codex or 'missing'}")
    if resolved_codex is None:
        issues.append("codex binary not found in PATH")

    if shim_path.exists():
        print(f"shim: present at {shim_path}")
        if _is_codex_shim(shim_path):
            real_bin = _resolve_real_codex_binary(shim_path)
            print(f"shim target: {real_bin or 'unknown'}")
        else:
            print("shim target: not a codex-hotswap shim")
            issues.append(f"{shim_path} exists but is not a codex-hotswap shim")
    else:
        print(f"shim: missing at {shim_path}")

    if resolved_codex is not None and shim_path.exists():
        try:
            same_path = Path(resolved_codex).resolve() == shim_path.resolve()
        except OSError:
            same_path = False
        print(f"shim active on PATH: {'yes' if same_path else 'no'}")
        if _is_codex_shim(shim_path) and not same_path:
            issues.append("codex shim is installed but is not the codex binary currently used from PATH")

    active_target_metadata = shared_home / ACTIVE_TARGET_METADATA
    if active_target_metadata.exists():
        try:
            payload = json.loads(active_target_metadata.read_text())
        except (json.JSONDecodeError, OSError):
            print("shared auth source: unreadable")
            issues.append("shared auth metadata is unreadable")
        else:
            metadata_target = payload.get("target") or "unknown"
            activated_at = payload.get("activated_at") or "unknown"
            print(f"shared auth source: {metadata_target}")
            print(f"shared auth activated at: {activated_at}")
    else:
        print("shared auth source: unknown")

    lock_path = shared_home / RUNTIME_LOCK_FILENAME
    lock_status, lock_detail = _probe_runtime_lock(lock_path)
    print(f"shared home lock: {lock_status}")
    if lock_detail:
        print(f"shared home lock detail: {lock_detail}")
    if lock_status == "error":
        issues.append("shared home lock could not be inspected")

    for target in config.targets:
        vault = Path(target.expanded_codex_home()) if target.expanded_codex_home() else None
        prefix = f"target {target.name}"
        print(f"{prefix}: {'active' if target.active else 'inactive'}")
        if vault is None:
            print(f"{prefix} auth vault: missing config")
            issues.append(f"{target.name} has no auth vault path configured")
            continue
        print(f"{prefix} auth vault: {vault}")
        if not vault.exists():
            print(f"{prefix} auth vault status: missing")
            issues.append(f"{target.name} auth vault directory is missing")
            continue

        auth_path = vault / "auth.json"
        if auth_path.exists():
            print(f"{prefix} auth.json: present")
        else:
            print(f"{prefix} auth.json: missing")
            issues.append(f"{target.name} auth.json is missing")
            continue

        if skip_login_status:
            print(f"{prefix} login status: skipped")
            continue

        logged_in, status_text = runner.login_status(target)
        if logged_in:
            print(f"{prefix} login status: ok")
        else:
            print(f"{prefix} login status: not authenticated")
            issues.append(f"{target.name} login status check failed")
        if status_text:
            print(f"{prefix} login detail: {status_text}")

    if issues:
        print("doctor status: issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("doctor status: ok")
    return 0


def _probe_runtime_lock(lock_path: Path) -> tuple[str, str | None]:
    if not lock_path.exists():
        return "idle", None
    try:
        with lock_path.open("a+", encoding="utf-8") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.seek(0)
                detail = handle.read().strip() or None
                return "busy", detail
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.seek(0)
                detail = handle.read().strip() or None
                return "idle", detail
    except OSError as exc:
        return "error", str(exc)


if __name__ == "__main__":
    raise SystemExit(main())
