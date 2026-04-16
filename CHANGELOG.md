# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows semantic versioning loosely during early development.

## [Unreleased]

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
