#!/bin/sh
# Prepares a folder to be a TraceForge project.
#
# Written by TraceForge, run by you: this product runs commands in a throwaway worktree at HEAD, and a
# folder with no repository has no HEAD to offer. Read it before you run it.
#
# Safe to run twice: every step checks first, and nothing here removes, moves or overwrites anything
# it did not create.
#
# Anything that would outlive this folder - installing a tool onto your machine, fetching a Python
# runtime into a shared cache - is asked about first, with the command shown. Anything but a typed
# "yes" declines it, and so does having no terminal.
set -e

SKIPPED=''

skip() {
  SKIPPED="${SKIPPED}
  - $1
      $2"
}

allow() {
  echo
  echo "This would change something outside this folder:"
  echo "  $2"
  if [ ! -t 0 ]; then
    echo "  Nothing is reading this terminal, so it is being treated as declined."
    return 1
  fi
  printf '%s [type yes to allow] ' "$1"
  read reply
  [ "$reply" = "yes" ]
}

if [ -d .git ]; then
  echo "Git repository: already here"
else
  git init -q
  echo "Git repository: created"
fi

if [ -f .gitignore ]; then
  echo ".gitignore: already here, leaving it alone"
  if ! grep -q '\.venv' .gitignore; then
    echo "            It does not mention .venv/, and this script is about to create one."
    echo "            Add a line reading .venv/ to it, or the environment will be committed."
  fi
else
  printf '%s\n' '.traceforge/cache/' '.traceforge/ui-state.json' '.venv/' > .gitignore
  echo ".gitignore: written"
fi

if git rev-parse HEAD >/dev/null 2>&1; then
  echo "First commit: already made"
else
  git add -A
  git commit -q -m "Initial commit"
  echo "First commit: made"
fi

# From here on, everything is created after the commit, so that nothing large is swept into it.

if [ -d .venv ]; then
  echo "Python environment: already here"
elif command -v uv >/dev/null 2>&1 && uv venv .venv --python '>=3.11' --no-python-downloads >/dev/null 2>&1; then
  echo "Python environment: created by uv, from a Python already on this machine"
elif command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  python3 -m venv .venv
  echo "Python environment: created by python3"
elif command -v uv >/dev/null 2>&1; then
  if allow "uv has no Python 3.11 or newer to work with and would fetch one." "uv venv .venv --python 3.11    (writes a Python into uv's own cache)"; then
    uv venv .venv --python 3.11
    echo "Python environment: created by uv, with a Python it fetched"
  else
    skip "Python environment" "uv venv .venv --python 3.11"
  fi
elif allow "Neither uv nor a Python 3.11 or newer is on this machine." "curl -LsSf https://astral.sh/uv/install.sh | sh    (writes uv into ~/.local/bin)"; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  "$HOME/.local/bin/uv" venv .venv --python 3.11
  echo "Python environment: created by uv, which was just fetched"
else
  skip "Python environment" "curl -LsSf https://astral.sh/uv/install.sh | sh, then: uv venv .venv --python 3.11"
fi

UV=''
if command -v uv >/dev/null 2>&1; then
  UV=uv
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV="$HOME/.local/bin/uv"
fi

if [ ! -d .venv ]; then
  skip "Spec Kit and Graphify" "they need the Python environment above"
elif [ -x .venv/bin/specify ] && [ -x .venv/bin/graphify ]; then
  echo "Spec Kit and Graphify: already here"
elif [ -n "$UV" ]; then
  "$UV" pip install --python .venv/bin/python graphifyy specify-cli
  echo "Spec Kit and Graphify: added to the environment"
else
  .venv/bin/pip install graphifyy specify-cli
  echo "Spec Kit and Graphify: added to the environment"
fi

if [ -x .venv/bin/specify ]; then
  echo "  specify:  $(.venv/bin/specify --version 2>&1 | head -1)"
fi
if [ -x .venv/bin/graphify ]; then
  echo "  graphify: $(.venv/bin/graphify --version 2>&1 | head -1)"
fi

if [ -d .specify ]; then
  echo "Spec Kit project: already initialised"
elif [ -x .venv/bin/specify ]; then
  .venv/bin/specify init --here --integration claude --force
  echo "Spec Kit project: initialised"
else
  skip "Spec Kit project" "it needs the Spec Kit CLI above"
fi

echo
if [ -n "$SKIPPED" ]; then
  echo "Skipped, and how to do each by hand:${SKIPPED}"
  echo
fi
echo "Done. Go back to TraceForge and press Verify."
