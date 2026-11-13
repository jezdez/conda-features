# Source only from a disposable bash --noprofile --norc shell.
set -euo pipefail

DEMO_REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
export DEMO_REPO
[[ ! -L "$DEMO_REPO/demos/.scratch" ]] || exit 1
mkdir -p -- "$DEMO_REPO/demos/.scratch"
demo_root=$(mktemp -d "$DEMO_REPO/demos/.scratch/recording.XXXXXX") || exit 1
readonly demo_root
trap '[[ "$demo_root" == "$DEMO_REPO/demos/.scratch/recording."* && -d "$demo_root" && ! -L "$demo_root" ]] && rm -rf -- "$demo_root"' EXIT

# Discard inherited configuration, Python injection, and shell initialization.
for name in $(compgen -v CONDA); do unset "$name"; done
unset PYTHONHOME PYTHONPATH PYTHONOPTIMIZE BASH_ENV ENV PROMPT_COMMAND NO_COLOR FORCE_COLOR
unset PIP_CONFIG_FILE PIP_INDEX_URL PIP_EXTRA_INDEX_URL
unset -f conda 2>/dev/null || true
export HOME="$demo_root/home" USERPROFILE="$demo_root/home"
export XDG_CONFIG_HOME="$HOME/.config" XDG_CACHE_HOME="$HOME/.cache"
export XDG_DATA_HOME="$HOME/.local/share" XDG_STATE_HOME="$HOME/.local/state"
export PIP_CONFIG_FILE=/dev/null
export TMPDIR="$demo_root/tmp" PYTHONNOUSERSITE=1
export CONDARC="$HOME/demo/.condarc"
export CONDA_PKGS_DIRS="$HOME/.cache/conda/pkgs" CONDA_ENVS_PATH="$HOME/envs"
export CONDA_OFFLINE=true CONDA_NO_PLUGINS=false
export PYTHONPATH="$DEMO_REPO/demos/_python"
export HISTFILE=/dev/null TERM=xterm-256color
export PS1="${DEMO_PS1:-\$ }"
mkdir -p -- "$HOME/demo" "$TMPDIR" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
cp -- "$DEMO_REPO/demos/condarc" "$CONDARC"
cd -- "$HOME/demo"
python -c 'import os; from conda.base.constants import SEARCH_PATH; assert SEARCH_PATH == (os.environ["CONDARC"],), "Demo isolation was not loaded."; from conda_features.steps.packages import missing_packages; assert not missing_packages(("conda-pypi>=0.13", "conda-rattler-solver>=26.10", "conda-completion==0.3.2")), "Install the demos environment before recording."'
