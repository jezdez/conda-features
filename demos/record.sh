#!/usr/bin/env bash
set -euo pipefail
unset BASH_ENV ENV PROMPT_COMMAND PYTHONOPTIMIZE
[[ $# -le 1 ]] || { printf 'Pass at most one demo name.\n' >&2; exit 2; }

case "${1:-}" in
    "") tapes=(feature-management configuration) ;;
    feature-management|configuration) tapes=("$1") ;;
    *) printf 'Choose feature-management or configuration.\n' >&2; exit 2 ;;
esac

for name in "${tapes[@]}"; do
    vhs validate "demos/$name.tape"
    vhs "demos/$name.tape"
done
