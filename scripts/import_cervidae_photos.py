"""Import user-selected species photos without changing the frozen taxonomy."""

import argparse
import json
import re
import shutil
import tempfile
import unicodedata
import zipfile
from pathlib import Path


def normalized(name):
    """Compare names without accents, case, punctuation, or spacing."""
    return re.sub(
        r"[^a-z0-9]",
        "",
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower(),
    )


ALIASES = {
    "northernredmuntjac": "indianmuntjac",
    "southernredmuntjac": "indianmuntjac",
    "reindeer": "caribou",
    "europeanfallowdeer": "commonfallowdeer",
    "javanrusa": "javanrusadeer",
    "sambardeer": "sambar",
    "reevessmuntjac": "reevesmuntjac",
    "rooseveltsmuntjac": "roosveltsmuntjac",
}


def import_photos(folder: Path, destination: Path, *, review_backup=None):
    """Keep photo bytes intact, record provenance, and prefer non-Artist files."""
    files = sorted(
        path
        for path in folder.glob("*/*")
        if path.parent.name in {"Cervinae", "Capreolinae"}
        and path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    regular = {normalized(p.stem): p for p in files if "[artist]" not in p.stem.lower()}
    with zipfile.ZipFile(destination) as original:
        records = json.loads(original.read("species.json"))
        metadata = json.loads(original.read("images/metadata.json"))
        review = json.loads(original.read("images/review.json"))
        if review_backup is not None:
            # Recover the pre-import review from the saved offline editor.
            review = {
                name: choice
                for name, choice in review.items()
                if name.startswith("images/user/")
            }
            review.update(review_backup)
        matched = {}
        missing = []
        for record in records:
            name = normalized(record["common_name"])
            photo = regular.get(ALIASES.get(name, name))
            if photo is None:
                missing.append(record["common_name"])
            else:
                matched[record["id"]] = photo
        # All supplied alternatives remain in the archive, even if not selected.
        entries = {
            f"images/user/{p.parent.name}/{p.name}": p.read_bytes() for p in files
        }
        for identifier, photo in matched.items():
            path = f"images/user/{photo.parent.name}/{photo.name}"
            metadata = [
                m
                for m in metadata
                if not (m["archive_name"] == path and m.get("subject") == identifier)
            ]
            metadata.append({
                "archive_name": path,
                "subject": identifier,
                "kind": "species",
                "file_title": photo.name,
                "description_url": "",
                "source": "User-supplied local photo",
                "mapping_note": (
                    "User-approved shared representative for Northern and Southern red muntjac; not a species-specific identification"
                    if normalized(photo.stem) == "indianmuntjac"
                    else "Matched by species name"
                ),
                "license": "Not supplied; verify redistribution rights before publishing",
            })
            review[path] = {"role": "photo", "crop": [0, 0, 1, 1]}
        report = {
            "matched_species": len(matched),
            "missing_species": missing,
            "unused_files": [p.name for p in files if p not in matched.values()],
            "license_note": "User-supplied images are not asserted to be Creative Commons.",
        }
        entries["images/metadata.json"] = (
            json.dumps(metadata, indent=2) + "\n"
        ).encode()
        entries["images/review.json"] = (json.dumps(review, indent=2) + "\n").encode()
        entries["images/user/import.json"] = (
            json.dumps(report, indent=2) + "\n"
        ).encode()
        with tempfile.TemporaryDirectory(dir=destination.parent) as staging:
            updated = Path(staging) / destination.name
            with zipfile.ZipFile(updated, "w", zipfile.ZIP_DEFLATED) as target:
                for entry in original.infolist():
                    if entry.filename not in entries:
                        target.writestr(entry, original.read(entry.filename))
                for name, data in entries.items():
                    target.writestr(name, data)
            with zipfile.ZipFile(updated) as target:
                assert target.testzip() is None
            original.close()
            shutil.copyfile(updated, destination)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    import_photos(
        args.folder,
        Path(__file__).resolve().parents[1] / "examples/data/cervidae-tree.zip",
    )
