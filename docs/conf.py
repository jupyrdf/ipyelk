"""documentation for ipyelk"""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sphinx.application import Sphinx

# our project data
HERE = Path(__file__).parent
ROOT = HERE.parent

RTD = "READTHEDOCS"

if os.getenv(RTD) == "True":
    # provide a fake root doc
    root_doc = "rtd"

    def setup(app: "Sphinx") -> None:
        """Customize the sphinx build lifecycle."""

        def _run_pixi(*_args: Any) -> None:
            args = ["pixi", "run", "-v", "docs-rtd"]
            env = {k: v for k, v in os.environ.items() if k != RTD}
            subprocess.check_call(args, env=env, cwd=str(ROOT))

        app.connect("build-finished", _run_pixi)

else:
    try:
        import tomllib
    except Exception:
        import tomli as tomllib

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
    copyright = f"""2020 {author}"""
    release = PROJ["version"]

    # paths
    exclude_patterns = [
        "_build",
        "Thumbs.db",
        ".DS_Store",
        ".ipynb_checkpoints",
        "rtd.rst",
    ]

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
