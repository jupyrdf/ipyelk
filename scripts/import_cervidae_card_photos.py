"""Add named wildlife photos as card-only overrides in the frozen ZIP."""

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from import_cervidae_photos import normalized


def import_cards(folder, destination):
    """Preserve originals, review choices, and tree photos while adding cards."""
    files = sorted(
        p
        for p in folder.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    with zipfile.ZipFile(destination) as original:
        species = json.loads(original.read("species.json"))
        by_name = {normalized(r["common_name"]): r["id"] for r in species}
        metadata = json.loads(original.read("images/metadata.json"))
        review = json.loads(original.read("images/review.json"))
        added, unmatched, entries = [], [], {}
        for photo in files:
            identifier = by_name.get(normalized(photo.stem))
            if identifier is None:
                unmatched.append(photo.name)
                continue
            path = f"images/user-cards/{photo.name}"
            entries[path] = photo.read_bytes()
            metadata = [m for m in metadata if m["archive_name"] != path]
            metadata.append({
                "archive_name": path,
                "subject": identifier,
                "kind": "card_photo",
                "file_title": photo.name,
                "description_url": "",
                "source": "User-supplied wildlife card photo",
                "license": "Not supplied; verify redistribution rights before publishing",
            })
            review.setdefault(path, {"role": "photo", "crop": [0, 0, 1, 1]})
            added.append(identifier)
        entries["images/metadata.json"] = (
            json.dumps(metadata, indent=2) + "\n"
        ).encode()
        entries["images/review.json"] = (json.dumps(review, indent=2) + "\n").encode()
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
    print(json.dumps({"added": added, "unmatched_files": unmatched}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    import_cards(
        args.folder,
        Path(__file__).resolve().parents[1] / "examples/data/cervidae-tree.zip",
    )
