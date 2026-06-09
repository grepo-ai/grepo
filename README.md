<h1 align="center">
  Grepo
</h1>

<p align="center">
  Agentic CLI for your terminal.
</p>

<p align="center">
  <video width="646" height="476" src="https://github.com/user-attachments/assets/78d521dd-c527-4111-b54e-33da8601fddd" controls></video>
</p>

## Status

Grepo is currently a work in progress. Expect breaking changes while the CLI,
protocol, and setup flow are still being refined.

## Setup

Grepo has two local pieces today:

- a Python backend package, installed from `src`
- a Bun-powered terminal UI, installed from `ui`

Prerequisites:

- Python 3.10.18 or newer
- Bun

From this repository checkout:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ./src

cd ui
bun install
bun link
```

Install the Python backend before linking the UI. Both packages currently define
a `grepo` command, so linking the UI last makes `grepo` start the Bun terminal
UI while still leaving the backend dependencies available to `python3`.

## Run From Any Repository

Run `grepo` from the repository you want Grepo to work on:

```sh
source /path/to/grepo/.venv/bin/activate
cd /path/to/your/repository
grepo
```

Grepo treats the current working directory as the target repository and creates
its local state in `.grepo/` inside that repository.

If `grepo` is not on your `PATH` after `bun link`, run the UI directly from any
repository:

```sh
source /path/to/grepo/.venv/bin/activate
cd /path/to/your/repository
bun /path/to/grepo/ui/bin/grepo.js
```

Set an API key before starting, or enter one when Grepo prompts you:

```sh
export ANTHROPIC_API_KEY="..."
```
