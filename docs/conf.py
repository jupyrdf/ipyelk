""" documentation for ipyelk
"""
# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import re
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

# our project data
HERE = Path(__file__).parent
ROOT = HERE.parent

PARSER = ConfigParser()
PARSER.read(str(ROOT / "setup.cfg"))
CFG = {s: dict(PARSER[s]) for s in PARSER.sections()}
META = CFG["metadata"]

# extensions
extensions = [
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
    "myst_nb",
]

# meta
project = META["name"]
copyright = f"""{datetime.now().year}, {META["author"]}"""
author = META["author"]
release = re.findall(
    r'''__version__ = "([^"]+)"''',
    (ROOT / "py_src/ipyelk/_version.py").read_text(encoding="utf-8"),
)[0]

# paths
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".ipynb_checkpoints"]

# content plugins
autosummary_generate = True

# theme
html_theme = "pydata_sphinx_theme"
html_logo = "_static/ipyelk.svg"
html_favicon = "_static/favicon.ico"

html_theme_options = {
    "github_url": META["url"],
    "use_edit_page_button": True,
    "show_toc_level": 1,
}
html_context = {
    "github_user": "jupyrdf",
    "github_repo": "ipyelk",
    "github_version": "master",
    "doc_path": "docs",
}
html_static_path = ["_static"]
