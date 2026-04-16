# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows semantic versioning loosely during early development.

## [Unreleased]

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
