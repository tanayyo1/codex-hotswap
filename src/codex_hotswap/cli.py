from __future__ import annotations

from pathlib import Path
import argparse
from dataclasses import replace
import shutil
import sys

from . import __version__
from .config import Config, ConfigError, DEFAULT_CONFIG_PATH, Settings, Target, load_config, save_config, write_default_config
from .runner import CodexRunner, format_target_line
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
                runner = CodexRunner(config=config, state_store=state_store)
                for target in generated_targets:
                    exit_code = runner.login(target, [])
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
    parser = argparse.ArgumentParser(prog="codex-hot")
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config.toml")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH, help="Path to state.json")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args(argv)

    try:
        config = load_config(parsed.config_path)
    except ConfigError as exc:
        print(f"codex-hotswap: {exc}", file=sys.stderr)
        return 1

    runner = CodexRunner(config=config, state_store=StateStore(parsed.state_path))
    return runner.run(_normalize_remainder(parsed.args))


def _normalize_remainder(values: list[str]) -> list[str]:
    if values and values[0] == "--":
        return values[1:]
    return values


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


if __name__ == "__main__":
    raise SystemExit(main())
