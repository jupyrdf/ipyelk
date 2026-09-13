"""Build an offline image review/crop page from the frozen Cervidae archive.

Run with the dev Python, then open build/cervidae-image-review.html. Export the
review JSON, then embed it with --import-review PATH. Originals are unchanged.
"""

import argparse
import base64
import json
import mimetypes
import shutil
import tempfile
import zipfile
from pathlib import Path


def import_review(archive_path: Path, review_path: Path):
    """Replace archived review choices, preserving every other entry verbatim."""
    review_bytes = review_path.read_bytes()
    review = json.loads(review_bytes)
    with zipfile.ZipFile(archive_path) as original:
        if not isinstance(review, dict) or set(review) - set(original.namelist()):
            raise ValueError("Review must map archived image paths to choices")
        with tempfile.TemporaryDirectory(dir=archive_path.parent) as staging:
            updated = Path(staging) / archive_path.name
            with zipfile.ZipFile(updated, "w", zipfile.ZIP_DEFLATED) as target:
                for entry in original.infolist():
                    if entry.filename != "images/review.json":
                        target.writestr(entry, original.read(entry.filename))
                target.writestr("images/review.json", review_bytes)
            with zipfile.ZipFile(updated) as target:
                if target.testzip() is not None:
                    raise ValueError("Updated archive failed integrity check")
            original.close()
            shutil.copyfile(updated, archive_path)


def build_review():
    """Embed archived images and existing review choices in a standalone page."""
    root = Path(__file__).resolve().parent.parent
    with zipfile.ZipFile(root / "examples/data/cervidae-tree.zip") as archive:
        review = (
            json.loads(archive.read("images/review.json"))
            if "images/review.json" in archive.namelist()
            else {}
        )
        records = json.loads(archive.read("images/metadata.json"))
        for record in records:
            name = record["archive_name"]
            mime = mimetypes.guess_type(name)[0] or "image/jpeg"
            record["data"] = (
                f"data:{mime};base64," + base64.b64encode(archive.read(name)).decode()
            )
    template = (
        Path(__file__)
        .with_name("cervidae_image_review.html")
        .read_text(encoding="utf-8")
    )
    data = json.dumps({"images": records, "review": review}).replace("<", "\\u003c")
    destination = root / "build/cervidae-image-review.html"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(template.replace("/* DATA */ null", data), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-review", type=Path)
    args = parser.parse_args()
    if args.import_review:
        import_review(
            Path(__file__).resolve().parent.parent / "examples/data/cervidae-tree.zip",
            args.import_review,
        )
    build_review()
