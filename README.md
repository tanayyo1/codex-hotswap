# codex-hotswap

[![CI](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml/badge.svg)](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.2.5-blue.svg)](https://github.com/tanayyo1/codex-hotswap)

`codex-hotswap` automatically switches Codex to another logged-in account when the current one hits usage limits, while keeping normal repo history and `/resume`.

## What This Does

If you use Codex heavily in the terminal, you eventually hit this:

- you are working in a repo
- your current Codex account runs out of usage
- your work stops
- you manually switch accounts and try to recover the session

`codex-hotswap` removes that manual account juggling.

You log into multiple Codex accounts once, then keep using normal `codex`.
When one account hits limits, `codex-hotswap` switches to the next one and resumes the session.

## Platform Support

- Linux: supported
- macOS: expected to work, but less field-tested
- Windows native: not supported yet
- Windows users should use WSL for now

## Start Here

If you just want the shortest setup path, do this.

### 1. Install `pipx` if you do not have it

On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Restart your shell after `pipx ensurepath`.

### 2. Install `codex-hotswap`

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
```

### 3. Set up 4 accounts

```bash
codex-hotswap setup --force --count 4 --prefix acc --login --install-shim
```

What this does:

- creates `acc1`, `acc2`, `acc3`, `acc4`
- asks you to log in to each account
- installs a small shim so normal `codex` runs through `codex-hotswap`

Each account login is still interactive. The command walks you through them one by one.

### 4. Pick the starting account

```bash
codex-hotswap use acc1
```

### 5. Use Codex normally

```bash
cd ~/your-repo
codex
```

That is the normal daily workflow after setup.

## What You Use Every Day

Most users only need:

```bash
cd ~/your-repo
codex
```

If the current account hits limits, `codex-hotswap` should rotate to the next account automatically.

## How It Works

`codex-hotswap` uses two layers of storage:

- shared runtime home: `~/.codex`
- per-account auth vaults: `~/.codex-acc1`, `~/.codex-acc2`, and so on

What stays shared:

- repo history
- normal `/resume`
- the active runtime session store

What stays separate:

- each account login

When a limit is hit:

1. the current account is marked exhausted
2. the next account auth is copied into the shared runtime home
3. `codex resume --last` is attempted

What should stay the same:

- repo directory
- normal `/resume` behavior
- overall session flow

What should change:

- the logged-in account

## Example

Example real use:

1. you are in `~/tonr`
2. you run `codex`
3. Codex is using `acc1`
4. `acc1` hits a usage limit
5. `codex-hotswap` switches to `acc2`
6. Codex continues in the same repo

The important signal is:

- same repo
- same general session/thread flow
- different `Account:` line

## Important Commands

```bash
codex-hotswap doctor
codex-hotswap status
codex-hotswap current
codex-hotswap use <target>
codex-hotswap next
codex-hotswap login <target>
codex-hotswap reset
codex-hotswap reset <target>
codex-hotswap install-shim
codex-hotswap uninstall-shim
```

What they mean:

- `codex-hotswap doctor` = check if setup is healthy
- `codex-hotswap status` = show targets and exhaustion state
- `codex-hotswap use acc1` = choose starting account
- `codex-hotswap login acc1` = log in one account
- `codex-hotswap reset` = clear exhausted markers

## If You Want Named Accounts Instead

Instead of `acc1`, `acc2`, `acc3`, `acc4`, you can use names:

```bash
codex-hotswap setup --force --accounts main,work,backup,extra --login --install-shim
```

## If You Want Device Auth

For headless or remote login:

```bash
codex-hotswap setup --force --count 4 --prefix acc --login --device-auth --install-shim
```

## Troubleshooting

### Check if everything is set up properly

```bash
codex-hotswap doctor
```

If you see:

```bash
doctor status: ok
```

your setup is healthy.

### `pipx: command not found`

On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Restart your shell, then install again.

### `codex-hotswap: Config file not found`

Create setup first:

```bash
codex-hotswap setup --force --count 4 --prefix acc
```

### It is not switching automatically

Check:

- you are using `codex` through the shim or `codex-hot`
- each account logged in successfully
- the target order in `codex-hotswap status`
- not all accounts are already exhausted

### `codex-hotswap: no non-exhausted targets remain`

This means every configured target is currently marked exhausted.

Check:

```bash
codex-hotswap status
```

Clear all exhaustion markers:

```bash
codex-hotswap reset
```

Or start from a specific account:

```bash
codex-hotswap use acc3
codex
```

### Another wrapped session is already using the shared home

Current design supports one wrapped session per shared runtime home.

If you need parallel wrapped sessions, use separate configs with different `shared_codex_home` values.

### `/resume` looks wrong

Make sure you are starting through `codex-hotswap`, not through a separate unmanaged Codex setup with another `CODEX_HOME`.

Use:

```bash
cd ~/your-repo
codex
```

## Guarantees And Limits

What it does well:

- keeps normal repo/session history in a shared Codex home
- preserves `/resume` behavior by repo
- isolates multiple account logins
- swaps account auth without changing your workspace

What it does not guarantee:

- perfect detection of every future Codex failure banner
- a real upstream usage meter from Codex
- perfect resume behavior if Codex changes its internals
- multiple wrapped sessions in the same shared runtime home

## FAQ

### Do I need to keep using `codex-hot`?

No. If you install the shim, you can just use normal `codex`.

### Will repo chats stay separate?

Yes. The shared runtime home keeps normal Codex history, so `/resume` should still stay organized by repo.

### Does it log into all accounts automatically?

No. You still log into each account once. After that, switching is automatic.

### Does it support native Windows?

No. Use WSL for now.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest
python -m build
```
