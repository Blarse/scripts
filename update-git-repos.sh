#!/bin/sh -efu

BASE_DIR="$HOME/alt/gears"

for repo in $(find "$BASE_DIR" -name ".git" -type d); do
    GIT_SSH_COMMAND="ssh -o BatchMode=yes" git --git-dir="$(readlink -f $repo)" fetch -q --all 2>/dev/null ||:
done
