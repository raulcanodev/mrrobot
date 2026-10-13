#!/usr/bin/env bash
#
# Installer for mrrobot.
#
#   curl -fsSL https://raw.githubusercontent.com/raulcanodev/mrrobot/main/install.sh | bash
#
# mrrobot is a Python package, so unlike a single-file script this sets up
# its own isolated virtual environment under ~/.local/share/mrrobot and
# links the `mrrobot` command into ~/.local/bin.

set -eu

REPOSITORY="${MRROBOT_REPOSITORY:-raulcanodev/mrrobot}"
BRANCH="${MRROBOT_BRANCH:-main}"
SHARE_DIR="${MRROBOT_SHARE_DIR:-$HOME/.local/share/mrrobot}"
BIN_DIR="${MRROBOT_BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$SHARE_DIR/venv"
SOURCE_URL="${MRROBOT_SOURCE_URL:-https://github.com/${REPOSITORY}/archive/refs/heads/${BRANCH}.tar.gz}"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mrrobot-install.XXXXXX")

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '%s is required to install mrrobot.\n' "$1" >&2
    exit 1
  fi
}

need curl
need tar

PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    version=$("$candidate" -c 'import sys; print(sys.version_info[:2] >= (3, 11))' 2>/dev/null || echo False)
    if [[ "$version" == "True" ]]; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  printf 'mrrobot needs Python 3.11 or newer. Install it (e.g. "brew install python") and try again.\n' >&2
  exit 1
fi

printf '\n  Installing mrrobot…\n'

curl -fsSL "$SOURCE_URL" -o "$WORK_DIR/source.tar.gz"
tar -xzf "$WORK_DIR/source.tar.gz" -C "$WORK_DIR"
SRC_DIR=$(find "$WORK_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)

# Rebuild the venv from scratch so a failed install never leaves a half
# working copy of the previous version in place.
rm -rf "$VENV_DIR"
mkdir -p "$SHARE_DIR"
"$PYTHON" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet "$SRC_DIR"

mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/mrrobot" "$BIN_DIR/mrrobot"

printf '  ✓ Installed at %s\n' "$BIN_DIR/mrrobot"

# Record which commit we just installed, so mrrobot can later check GitHub
# for a newer one and offer to self-update. Best-effort: a dev checkout, an
# offline install, or a rate-limited API call just means that check stays
# quiet later — it never fails the install itself.
RESOLVED_SHA=$(
  "$VENV_DIR/bin/python" - "https://api.github.com/repos/${REPOSITORY}/commits/${BRANCH}" <<'PYEOF' 2>/dev/null || true
import json
import sys
import urllib.request

try:
    req = urllib.request.Request(sys.argv[1], headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        print(json.load(resp)["sha"])
except Exception:
    pass
PYEOF
)
if [[ -n "$RESOLVED_SHA" ]]; then
  SELF_DATA_DIR=$("$VENV_DIR/bin/python" -c "from platformdirs import user_data_dir; print(user_data_dir('mrrobot'))")
  mkdir -p "$SELF_DATA_DIR"
  printf '%s\n' "$RESOLVED_SHA" > "$SELF_DATA_DIR/installed_commit.txt"
fi

# Tell the user when their shell cannot find the new command yet.
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    printf '\n  Add this line to ~/.zshrc, then open a new terminal:\n\n'
    printf '    export PATH="%s:$PATH"\n' "$BIN_DIR"
    ;;
esac

printf '\n  Run: mrrobot doctor\n\n'
