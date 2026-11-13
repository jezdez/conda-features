"""Private recording bootstrap, never installed with either distribution."""

from __future__ import annotations

import os

from conda.base import constants

# Patch before importing Context so its default arguments are isolated too.
constants.SEARCH_PATH = (os.environ["CONDARC"],)
