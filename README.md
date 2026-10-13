# mrrobot

A modular terminal orchestrator for **authorized OSINT & pentesting**.

`mrrobot` doesn't reimplement security tools: it **orchestrates** them. It
runs reputable open-source tools (Sherlock, subfinder, Nmap…) through
adapters, normalizes their results, keeps a history, and warns you when
updates are available. Built to grow: today it's a clean CLI; tomorrow,
without touching the core, it could have an interface (TUI/web).

> ⚖️ **Responsible use.** Designed for passive recon against public
> sources, and for active testing **only** against your own targets or with
> explicit authorization (labs, in-scope bug bounty programs, clients with
> written permission). Active actions are blocked unless the target is in
> your declared scope. You are responsible for how you use it.

## Architecture

```
src/mrrobot/
├── cli/                 # Thin terminal layer (Typer + Rich + questionary)
│   ├── app.py           #   commands: run, report, tools, scope, history, doctor
│   ├── menu.py          #   interactive menu (arrow-key selector)
│   ├── actions.py       #   logic shared between commands and the menu
│   ├── report_wizard.py #   interactive report wizard
│   ├── style.py         #   shared visual style for the selector
│   └── banner.py
├── core/                # Reusable core (independent of the UI)
│   ├── models.py        #   ToolMeta, RunResult, Scope, Mode, TargetKind…
│   ├── config.py        #   scope / authorization
│   ├── registry.py      #   central tool registry
│   ├── runner.py        #   external process execution
│   ├── installer.py     #   automatic install (brew/pipx)
│   ├── updates.py       #   installed version vs. latest release
│   ├── report.py        #   aggregating results into a report
│   └── storage.py       #   SQLite history
└── tools/               # One adapter per tool
    ├── osint/            # sherlock, theharvester, whois
    ├── web/               # subfinder, amass, crtsh, wayback
    └── network/           # nmap, internetdb, certinfo
```

**Execution modes**

| Mode | What it does | Authorization |
|------|----------|--------------|
| `passive` | Queries public sources, never touches the target | Allowed by default |
| `active`  | Sends traffic to the target | Requires authorized scope |

**Built-in tools** (10 right now, not counting what you add):

| Tool | Category | Mode | Install |
|---|---|---|---|
| `sherlock` | osint | passive | external (brew/pipx) — username on social networks |
| `theharvester` | osint | passive | external (brew) — emails/hosts via OSINT sources |
| `whois` | osint | passive | **built-in** — registrant, dates, authoritative DNS |
| `subfinder` | web | passive | external (brew) — subdomains |
| `amass` | web | passive | external (brew), always in `-passive` |
| `crtsh` | web | passive | **built-in** — subdomains via Certificate Transparency |
| `wayback` | web | passive | **built-in** — historical URLs (Internet Archive) |
| `nmap` | network | active | external (brew) — ports and services |
| `internetdb` | network | passive | **built-in** — Shodan snapshot (no API key) |
| `certinfo` | network | active | **built-in** — TLS certificate, SANs, cipher |

"Built-in" tools need nothing installed: they're written in Python inside
mrrobot and work from the very first `mrrobot doctor`.

## Install

Copy and paste this into your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/raulcanodev/mrrobot/main/install.sh | bash
```

Installs `mrrobot` in its own virtual environment under
`~/.local/share/mrrobot` and links the command into `~/.local/bin/mrrobot`,
without touching your system Python. Requires Python 3.11+ (e.g.
`brew install python`).

Then run:

```bash
mrrobot doctor
```

To update, run the same install command again. To uninstall:

```bash
rm ~/.local/bin/mrrobot
rm -rf ~/.local/share/mrrobot
```

### Development install

```bash
git clone https://github.com/raulcanodev/mrrobot.git
cd mrrobot
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

External tools install separately, one command each:

```bash
mrrobot tools install sherlock     # shows you the command (brew/pipx) and asks to confirm
```

## Usage

### Interactive menu

```bash
mrrobot
```

Run with nothing else, it opens an **arrow-key selector menu** (↑/↓ + Enter,
no typing commands): run a tool, generate a report, check tool status,
install the missing ones, manage scope, or view history. `mrrobot menu`
does the same thing explicitly. On startup it also does a quick,
best-effort check against GitHub for a newer mrrobot — if one's found,
it asks whether to update right there (see **Self-update** below).

This **doesn't replace** the command-line path: everything in the menu
also has its own direct command, for scripts, automation, or whenever you
already know what you want to run.

### Direct commands

```bash
mrrobot doctor                     # startup check + update notices
mrrobot tools --online             # built-in tools and their versions
mrrobot tools install <name>       # install one external tool
mrrobot tools install --all        # install every missing one in one go
mrrobot scope init                 # create your scope template
mrrobot run sherlock raulcanodev   # passive OSINT, a single tool
mrrobot run subfinder example.com  # subdomains (passive)
mrrobot run nmap 192.168.1.10      # network (active → requires scope)
mrrobot report                     # interactive wizard: full report
mrrobot history                    # previous runs
mrrobot update                     # check GitHub and update mrrobot itself
```

### Self-update

Installs made via `curl | install.sh` record the commit they were built
from. From then on, the menu (on startup) and `mrrobot doctor` do a quick,
best-effort check against GitHub's API for a newer commit on `main`, and
`mrrobot update` does the same on demand. If one's found, confirming
re-runs the official installer in place — the exact same command from
**Install** above — then asks you to restart mrrobot.

A dev/editable install (`pip install -e .`) has nothing to compare
against and stays silent about this on purpose, since you're the one
changing the code.

### Full reports (`mrrobot report`)

```
mrrobot report example.com
```

Asks whether to generate the report, confirms the kind of target
(domain/username/IP), and lets you pick which applicable tools to run with
checkboxes (space to toggle, Enter to continue). As it runs, each tool
shows a live spinner with its position in the batch and an elapsed-time
counter (`[3/8] Running theharvester (passive)… 0:00:42`), so you always
know what's running and for how long. When it's done:

- it prints a console summary (each tool in its own panel, with the first
  lines of output);
- it asks whether to save the **full report** to a `.txt` file under
  `~/.local/share/mrrobot/reports/`;
- it records every run in the history (`mrrobot history`).

ACTIVE tools outside your authorized scope aren't blocked with an error:
they're simply marked as "blocked" inside the report.

## Adding a tool

**External** (launches a binary):
1. Create `tools/<category>/<name>.py` subclassing `ToolAdapter`.
2. Declare its `ToolMeta` (binary, repo, mode, `target_kind`, `install_cmds`).
3. Override `build_args()`.

**Built-in** (no binary, e.g. a public API):
1. Same `ToolMeta`, with `builtin=True` and no `binary`.
2. Override `execute()` directly and build the result with `make_result()`
   (see `tools/web/crtsh.py` for a short example).

Either way, register it in `core/registry.py`. The rest (authorization,
history, reports, update notices) is already shared.

## License notes

Each tool keeps its own license. `mrrobot` runs them as external processes
(adapters); it never copies or redistributes their code.
