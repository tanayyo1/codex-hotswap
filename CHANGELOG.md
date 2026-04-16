# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows semantic versioning loosely during early development.

## [Unreleased]

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
