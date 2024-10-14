"""Apply prettier formatting to notebook markdown cells."""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path
from subprocess import call
from uuid import uuid4

import nbformat
import nbformat.validator

NBFORMAT_VERSION = (4, 5)

HERE = Path(__file__).parent
ROOT = HERE.parent
CELL_MD = ROOT / "build/nblint"
CELL_MD_GLOB = f"{CELL_MD}/**/*.md"
UTF8 = {"encoding": "utf8"}
UTF8_NL = {**UTF8, "newline": "\n"}
PRETTIER = ["jlpm", "prettier", "--write", CELL_MD_GLOB]


def handle_one_cell(
    cell: nbformat.NotebookNode,
    idx: int,
    nb_out: Path,
    *,
    fix: bool = False,
    write: bool = False,
) -> int:
    """Handle a single cell."""
    if "id" not in cell:
        cell["id"] = str(uuid4())
    if cell["cell_type"] != "markdown":
        return 0
    cell_out = nb_out / f"""cell-{idx + 1}.md"""
    if write:
        old = cell["source"]
        new = cell_out.read_text(**UTF8).strip()
        if old != new:
            if fix:
                print(f"... cell is now prettier: {cell_out.relative_to(CELL_MD)}")
            else:
                print(f"... cell is NOT pretty: {cell_out.relative_to(CELL_MD)}")
            if fix:
                cell["source"] = new
            else:
                return 1
    else:
        nb_out.mkdir(parents=True, exist_ok=True)
        cell_out.write_text(cell["source"].strip() + "\n", **UTF8_NL)
    return 0


def handle_one_nb(ipynb: Path, *, fix: bool = False, write: bool = False) -> int:
    """Handle a single notebook."""
    rel = str(ipynb.relative_to(ROOT))
    with ipynb.open(**UTF8) as nbfp:
        nb: nbformat.NotebookNode = nbformat.read(nbfp, as_version=4)
    nb["nbformat"], nb["nbformat_minor"] = NBFORMAT_VERSION
    nb_out = CELL_MD / rel

    try:
        error_count = sum(
            handle_one_cell(cell, idx, nb_out, fix=fix, write=write)
            for idx, cell in enumerate(nb["cells"])
        )
    except Exception as err:
        print(ipynb, err)
        error_count = 1

    if write and not error_count:
        if len(nb["cells"]) >= 1 and not nb["cells"][-1]["source"].strip():
            print(f"""... removed trailing empty cell from: {ipynb}""")
            nb["cells"] = nb["cells"][:-1]
        normalized = nbformat.NotebookNode(
            nbformat.validator.normalize(nb, *NBFORMAT_VERSION)[1]
        )
        with ipynb.open(mode="w", **UTF8) as nbfp:
            nbformat.write(normalized, nbfp)

    return error_count


def nblint(roots: list[Path], fix: bool = False) -> int:
    """Make the cells pretty."""
    shutil.rmtree(CELL_MD, ignore_errors=True)
    error_count = 0
    all_ipynb = []
    for root in roots:
        all_ipynb += sorted(
            p
            for p in root.resolve().rglob("*.ipynb")
            if "ipynb_checkpoints" not in str(p)
        )

    print("fixing" if fix else "checking", len(all_ipynb), "notebooks...")
    error_count += sum(handle_one_nb(path, fix=fix) for path in all_ipynb)
    if not error_count:
        error_count += call(PRETTIER)
    if not error_count:
        error_count += sum(
            handle_one_nb(path, fix=fix, write=True) for path in all_ipynb
        )
    return error_count


def get_parser() -> ArgumentParser:
    """Build a CLI parser."""
    parser = ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("roots", nargs="+", type=Path)
    return parser


if __name__ == "__main__":
    sys.exit(nblint(**vars(get_parser().parse_args())))
