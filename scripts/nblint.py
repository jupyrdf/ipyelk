""" linter and formatter of notebooks
"""
# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import black
import isort
import nbformat
from isort.api import sort_code_string

from . import project as P

NODE = [shutil.which("node") or shutil.which("node.exe") or shutil.which("node.cmd")]

NB_METADATA_KEYS = ["kernelspec", "language_info"]

ISORT_CONFIG = isort.settings.Config(settings_path=P.SETUP_CFG)


def blacken(source):
    """apply black to a source string"""
    return black.format_str(source, mode=black.FileMode(line_length=88))


def nblint_one(nb_node):
    """format/lint one notebook"""
    changes = 0
    has_empty = 0
    nb_metadata_keys = list(nb_node.metadata.keys())
    for key in nb_metadata_keys:
        if key not in NB_METADATA_KEYS:
            nb_node.metadata.pop(key)
    for cell in nb_node.cells:
        cell_type = cell["cell_type"]
        source = "".join(cell["source"])
        if not source.strip():
            has_empty += 1
        if cell_type == "markdown":
            args = [
                *P.PRETTIER,
                "--stdin-filepath",
                "foo.md",
                "--prose-wrap",
                "always",
            ]
            prettier = subprocess.Popen(
                list(map(str, args)),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            out, _err = prettier.communicate(source.encode("utf-8"))
            new = out.decode("utf-8").rstrip()
            if new != source:
                cell["source"] = new.splitlines(True)
                changes += 1
        elif cell_type == "code":
            if cell["outputs"] or cell["execution_count"]:
                cell["outputs"] = []
                cell["execution_count"] = None
                changes += 1
            if [line for line in source.splitlines() if line.strip().startswith("!")]:
                continue
            if source.startswith("%"):
                continue
            new = sort_code_string(source, config=ISORT_CONFIG)
            new = blacken(new).rstrip()
            if new != source:
                cell["source"] = new.splitlines(True)
                changes += 1

    if has_empty:
        changes += 1
        nb_node.cells = [
            cell for cell in nb_node.cells if "".join(cell["source"]).strip()
        ]

    return nb_node


def nb_hash(nb_text):
    """hash one notebook"""
    return sha256(nb_text.encode("utf-8")).hexdigest()


def nblint(nb_paths):
    """lint a number of notebook paths"""
    len_paths = len(nb_paths)

    for i, nb_path in enumerate(nb_paths):
        nb_text = nb_path.read_text(encoding="utf-8")
        pre_hash = nb_hash(nb_text)

        if len_paths > 1:
            print(f"[{i + 1} of {len_paths}] {nb_path}", flush=True)

        nb_node = nblint_one(nbformat.reads(nb_text, 4))

        with nb_path.open("w", encoding="utf-8") as fpt:
            nbformat.write(nb_node, fpt)

        post_hash = nb_hash(nb_path.read_text(encoding="utf-8"))

        if post_hash != pre_hash:
            print(f"\t{nb_path.name} formatted")

    return 0


if __name__ == "__main__":
    sys.exit(nblint([Path(p) for p in sys.argv[1:]] or P.EXAMPLE_IPYNB))
