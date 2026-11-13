"""Documentation for the conda feature-management plugin."""

project = "conda-features"
author = "conda-features contributors"
extensions = ["myst_parser", "sphinx_design"]
html_theme = "conda_sphinx_theme"
myst_enable_extensions = ["colon_fence"]
myst_heading_anchors = 3
exclude_patterns = ["_build"]
html_title = "conda-features documentation"
