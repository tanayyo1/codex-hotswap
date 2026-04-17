# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows semantic versioning loosely during early development.

## [Unreleased]

## [0.3.1]

### Fixed

- Made `codex-hotswap disable` prime the shared `~/.codex/auth.json` from the current target before removing the shim, so plain `codex` works immediately for fresh installs.
- Stopped `enable` and `disable` tests from accidentally depending on a real machine config.

## [0.3.0]

### Changed

- Replaced the single shared wrapped runtime with per-session runtime overlays, so wrapped Codex sessions can run in parallel while still sharing the normal Codex history store.
- Kept account auth private to each wrapped session by copying `auth.json` into the overlay instead of mutating the shared store in place.
- Updated `doctor` and the README to describe the overlay model and parallel wrapped-session support.

### Added

- Added runtime overlay coverage to the test suite for shared-store links, private auth, and concurrent wrapped-session setup.

## [0.2.6]

### Added

- Added `codex-hotswap enable` and `codex-hotswap disable` as simpler aliases for turning the normal `codex` shim on and off.

### Changed

- Clarified the README around the single wrapped-session design and the fallback flow for plain multi-session Codex use.

## [0.2.5]

### Fixed

- Replaced Windows import crashes with explicit platform-support errors and guidance to use WSL for now.
- Stopped advertising the package as OS-independent in metadata.

## [0.2.4]

### Fixed

- Refused to overwrite non-shim files during `install-shim`, even when `--force` is used.
- Converted malformed `config.toml` and `state.json` files into clean user-facing errors instead of Python tracebacks.
- Stopped binary resolution from depending on an inherited `CODEX_HOTSWAP_REAL_BIN` environment variable.

## [0.2.3]

### Fixed

- Forwarded unknown top-level shim arguments like `codex --version` to the real Codex CLI instead of rejecting them in the wrapper parser.
- Isolated doctor tests from machine-specific shim state.

## [0.2.2]

### Changed

- Rewrote the README around the actual install, setup, shim, and troubleshooting flow.
- Added active-auth metadata in the shared home so `doctor` can report which target last populated shared auth.
- Made `doctor` treat an installed-but-inactive shim as a real configuration issue.

### Fixed

- Prevented concurrent wrapped sessions from mutating the same shared `CODEX_HOME` at the same time by adding a shared-home runtime lock.

## [0.2.1]

### Changed

- Added a one-command setup path that can create targets, log them in, and install the `codex` shim in one shot.
- Made binary resolution skip the shim automatically so setup and login paths do not recurse into wrapped `codex`.
- Added a `doctor` command to verify the shared home, auth vaults, current target, and shim wiring.
- Tightened setup validation so login-only flags and shim-only flags cannot be passed in meaningless combinations.

## [0.2.0]

### Changed

- Switched runtime launches to a shared Codex home so repo/session history and `/resume` stay normal.
- Moved multi-account handling to per-account auth vaults that are copied into the shared home before launch.
- Clarified setup and README language around auth vaults versus the shared runtime home.
- Added optional `codex` shim install/uninstall commands so plain `codex` can route through hotswap.

### Fixed

- Preserved existing repo-specific session history when rotating accounts.

## [0.1.4]

### Changed

- Narrowed live trigger detection so generic chat text is less likely to cause accidental account rotation.
- Made `setup` reruns update existing generated targets instead of failing on duplicate names.
- Improved README troubleshooting and setup notes around conservative live detection.

### Fixed

- Guarded swap-time signals against child-process races that could crash the wrapper during rotation.
- Handled missing `codex` binaries more cleanly during `login status` checks.

### Added

- Multi-target Codex wrapper with automatic rotation and `codex resume --last` recovery.
- Isolated account support via per-target `CODEX_HOME`.
- Cooldown-aware exhaustion tracking.
- Target login command.
- Target add/remove management commands.
- GitHub Actions CI for tests and package builds.
