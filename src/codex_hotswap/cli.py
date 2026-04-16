from __future__ import annotations

from pathlib import Path
import argparse
import sys

from .config import ConfigError, DEFAULT_CONFIG_PATH, load_config, write_default_config
from .runner import CodexRunner, format_target_line
from .state import DEFAULT_STATE_PATH, StateStore


def build_parser(argv0: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=argv0)
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config.toml")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH, help="Path to state.json")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config.toml")
    common.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH, help="Path to state.json")

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Write a starter config", parents=[common])
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing config")

    subparsers.add_parser("list", help="List configured targets", parents=[common])
    subparsers.add_parser("status", help="Show configured targets and current state", parents=[common])
    subparsers.add_parser("current", help="Print the current target", parents=[common])

    use_parser = subparsers.add_parser("use", help="Set the active target", parents=[common])
    use_parser.add_argument("target")

    next_parser = subparsers.add_parser("next", help="Rotate to the next available target", parents=[common])
    next_parser.add_argument("--print-only", action="store_true", help="Do not update state")

    exhaust_parser = subparsers.add_parser("exhaust", help="Mark a target as exhausted", parents=[common])
    exhaust_parser.add_argument("target")
    exhaust_parser.add_argument("--reason", default="manual")

    reset_parser = subparsers.add_parser("reset", help="Clear exhaustion markers", parents=[common])
    reset_parser.add_argument("target", nargs="?")

    run_parser = subparsers.add_parser("run", help="Run codex through the hotswap wrapper", parents=[common])
    run_parser.add_argument("args", nargs=argparse.REMAINDER)

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
        state_store.mark_exhausted(state, args.target, args.reason)
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


if __name__ == "__main__":
    raise SystemExit(main())
