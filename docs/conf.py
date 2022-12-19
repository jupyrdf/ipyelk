""" documentation for ipyelk
"""
# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from datetime import datetime
from pathlib import Path

try:
    import tomllib
except Exception:
    import tomli as tomllib

# our project data
HERE = Path(__file__).parent
ROOT = HERE.parent

PY_PROJ = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
PROJ = PY_PROJ["project"]

# extensions
extensions = [
    "myst_nb",
    # "autodoc_traits",  # TODO investigate if can help streamline documentation writing
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
]

# meta
project = PROJ["name"]
author = PROJ["authors"][0]["name"]
copyright = f"""{datetime.now().year}, {author}"""
release = PROJ["version"]

# paths
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".ipynb_checkpoints"]

# content plugins
autosummary_generate = True

# theme
html_theme = "pydata_sphinx_theme"
html_logo = "_static/ipyelk.svg"
html_favicon = "_static/favicon.ico"

html_theme_options = {
    "github_url": PROJ["urls"]["Source"],
    "use_edit_page_button": True,
    "show_toc_level": 1,
}
html_context = {
    "github_user": "jupyrdf",
    "github_repo": "ipyelk",
    "github_version": "master",
    "doc_path": "docs",
}
html_static_path = ["_static", "../build/lite"]
