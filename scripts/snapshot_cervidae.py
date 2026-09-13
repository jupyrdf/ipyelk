# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
# ruff: file-ignore[suspicious-url-open-usage]
"""Create the pinned data archive used by the Cervidae example notebook.

The archive deliberately stores a Wikipedia revision and Commons image metadata,
so the notebook does not change when either site is edited later.  The resulting
ZIP is tracked through Git LFS; see ``examples/data/README.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from bs4.element import Tag

ARCHIVE = Path("examples/data/cervidae-tree.zip")
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "ipyelk-cervidae-example/1.0 (https://github.com/jupyrdf/ipyelk)"
SPECIES_TABLE_COLUMNS = 5
EXPECTED_SPECIES_COUNT = 55

# This is the display hierarchy. The raw List of cervids revision in the archive
# contains the complete species-level table and its supporting information.
TAXONOMY = {
    "Cervidae": {
        "Cervinae": {
            "Muntiacini": ["Elaphodus", "Muntiacus"],
            "Cervini": [
                "Axis",
                "Cervus",
                "Dama",
                "Elaphurus",
                "Panolia",
                "Rucervus",
                "Rusa",
            ],
        },
        "Capreolinae": {
            "Alceini": ["Alces"],
            "Capreolini": ["Capreolus", "Hydropotes"],
            "Odocoileini": [
                "Blastocerus",
                "Hippocamelus",
                "Mazama",
                "Odocoileus",
                "Ozotoceros",
                "Pudu",
                "Rangifer",
            ],
        },
    }
}

# Some genus articles have no lead image, or their lead image is a range map.
# Use a representative extant species page instead. The page-image API supplies
# the Commons file name, whose metadata is stored alongside the downloaded image.
REPRESENTATIVE_PAGES = {
    "Alces": "Moose",
    "Axis": "Chital",
    "Blastocerus": "Marsh deer",
    "Capreolus": "Roe deer",
    "Cervus": "Red deer",
    "Dama": "Fallow deer",
    "Elaphodus": "Tufted deer",
    "Elaphurus": "Père David's deer",
    "Hippocamelus": "Taruca",
    "Hydropotes": "Water deer",
    "Mazama": "Red brocket",
    "Muntiacus": "Muntjac",
    "Odocoileus": "White-tailed deer",
    "Ozotoceros": "Pampas deer",
    "Panolia": "Barasingha",
    "Pudu": "Southern pudu",
    "Rangifer": "Reindeer",
    "Rucervus": "Barasingha",
    "Rusa": "Sambar deer",
}


def request_json(url: str, parameters: dict[str, str]) -> dict[str, Any]:
    """Fetch JSON from a Wikimedia API endpoint."""
    query = urllib.parse.urlencode(parameters)
    request = urllib.request.Request(
        f"{url}?{query}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def request_bytes(url: str) -> bytes:
    """Download a Commons asset."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def wikipedia_revision() -> dict[str, Any]:
    """Return the exact source revision and wikitext used by this archive."""
    data = request_json(
        WIKIPEDIA_API,
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
            "titles": "List of cervids",
        },
    )
    page = data["query"]["pages"][0]
    revision = page["revisions"][0]
    return {
        "page_id": page["pageid"],
        "page_title": page["title"],
        "revision_id": revision["revid"],
        "timestamp": revision["timestamp"],
        "wikitext": revision["slots"]["main"]["content"],
    }


def wikipedia_html(revision_id: int) -> str:
    """Render the pinned source revision to HTML for deterministic table extraction."""
    data = request_json(
        WIKIPEDIA_API,
        {
            "action": "parse",
            "format": "json",
            "oldid": str(revision_id),
            "prop": "text",
        },
    )
    return data["parse"]["text"]["*"]


def table_text(cell: Tag) -> str:
    """Convert a Wikipedia table cell to a compact plain-text value."""
    for reference in cell.select("sup.reference"):
        reference.decompose()
    text = " ".join(cell.stripped_strings).replace("�", "-")
    return re.sub(r"\s+", " ", text).strip()


def ecology_fields(ecology: str) -> dict[str, str]:
    """Split the source's labelled ecology column into displayable fields."""
    fields = {"size": "", "habitat": "", "diet": ""}
    boundaries = list(re.finditer(r"(Size|Habitat|Diet)\s*:\s*", ecology))
    for index, match in enumerate(boundaries):
        end = boundaries[index + 1].start() if index + 1 < len(boundaries) else None
        fields[match.group(1).lower()] = ecology[match.end() : end].strip()
    return fields


def status_fields(status: str) -> dict[str, str]:
    """Separate the IUCN code from the population and trend text."""
    match = re.match(r"(?P<code>EX|EW|CR|EN|VU|NT|LC|DD|NE)\s*(?P<rest>.*)", status)
    if match is None:
        return {"status": status, "population": ""}
    return {"status": match.group("code"), "population": match.group("rest")}


def article_title(cell: Tag) -> str:
    """Return the linked Wikipedia article title for a source-table cell."""
    link = cell.select_one("a[href*='/wiki/'], a[href^='./']")
    if link is None:
        return ""
    href = urllib.parse.unquote(link["href"])
    return href.removeprefix("./").removeprefix("/wiki/").replace("_", " ")


def species_records(source_html: str) -> list[dict[str, str]]:
    """Extract the five published fields from every genus table in the source page."""
    document = BeautifulSoup(source_html, "html.parser")
    records: list[dict[str, str]] = []
    for genus in genera():
        table = next(
            (
                candidate
                for candidate in document.find_all("table", class_="wikitable")
                if candidate.caption is not None
                and f"Genus {genus}" in table_text(candidate.caption)
            ),
            None,
        )
        if table is None:
            msg = f"No source table found for {genus}"
            raise ValueError(msg)
        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) != SPECIES_TABLE_COLUMNS:
                continue
            common_name, _, range_text, ecology, status = map(table_text, cells)
            if common_name == "Common name":
                continue
            scientific_cell = cells[1].find("i") or cells[1]
            scientific_name = table_text(scientific_cell)
            records.append({
                "id": f"{genus}:{scientific_name}",
                "genus": genus,
                "common_name": common_name,
                "scientific_name": scientific_name,
                "article_title": article_title(cells[0]),
                "range_file": next(
                    (
                        urllib.parse.unquote(str(link.get("href", ""))).split("File:")[
                            -1
                        ]
                        for link in cells[2].select("a.mw-file-description")
                        if link.find("img") is not None
                    ),
                    "",
                ),
                "range": range_text,
                **ecology_fields(ecology),
                **status_fields(status),
            })
    if len(records) != EXPECTED_SPECIES_COUNT:
        msg = f"Expected 55 cervid species, found {len(records)}"
        raise ValueError(msg)
    return records


def wikipedia_image(
    title: str, archive_name: str, *, subject: str, kind: str
) -> tuple[str, bytes, dict[str, Any]] | None:
    """Freeze a Wikipedia page's lead image and Commons attribution metadata."""
    data = request_json(
        WIKIPEDIA_API,
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "rvprop": "ids",
            "redirects": "1",
            "piprop": "name|thumbnail",
            "pithumbsize": "640",
            "imlimit": "20",
            "titles": title,
        },
    )
    page = data["query"]["pages"][0]
    if not page.get("revisions"):
        return None
    revision_id = page["revisions"][0]["revid"]
    document = BeautifulSoup(wikipedia_html(revision_id), "html.parser")
    image_title = None
    for link in document.select("table.infobox a.mw-file-description"):
        if link.find("img") is None:
            continue
        filename = urllib.parse.unquote(str(link.get("href", ""))).split("File:")[-1]
        is_range = bool(
            re.search(r"range|distribution|map|habitat", filename, re.IGNORECASE)
        )
        if is_range != (kind == "range"):
            continue
        if kind != "range" and not filename.lower().endswith((
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )):
            continue
        image_title = filename
        break
    if not image_title:
        print(f"No usable image found for {title}; skipping it")
        return None

    return commons_image(
        image_title, archive_name, subject, kind, (page["title"], revision_id)
    )


def commons_image(image_title, archive_name, subject, kind, source_revision):
    """Download a named Commons asset with attribution and source revision."""
    article_title, revision_id = source_revision
    title = article_title
    commons = request_json(
        COMMONS_API,
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": "640",
            "titles": f"File:{image_title}",
        },
    )
    file_page = commons["query"]["pages"][0]
    if not file_page.get("imageinfo"):
        print(f"No Commons image for {image_title}; skipping it")
        return None
    image_info = file_page["imageinfo"][0]
    source_url = image_info["url"]
    thumbnail_url = image_info.get("thumburl")
    if not thumbnail_url:
        print(f"No usable thumbnail found for {title}; skipping it")
        return None
    suffix = Path(urllib.parse.urlparse(thumbnail_url).path).suffix.lower() or ".img"
    archive_name = f"{archive_name}{suffix}"
    metadata = {
        "subject": subject,
        "kind": kind,
        "article_title": article_title,
        "article_revision": revision_id,
        "selection_method": "Wikipedia source image link",
        "archive_name": archive_name,
        "file_title": file_page["title"],
        "source_url": source_url,
        "thumbnail_url": thumbnail_url,
        "description_url": image_info["descriptionurl"],
        "metadata": image_info.get("extmetadata", {}),
    }
    return archive_name, request_bytes(thumbnail_url), metadata


def genus_image(genus: str) -> tuple[str, bytes, dict[str, Any]] | None:
    """Retrieve a representative genus image and its attribution metadata."""
    return wikipedia_image(
        REPRESENTATIVE_PAGES[genus],
        f"images/genera/{genus.lower()}",
        subject=genus,
        kind="genus",
    )


def species_image(record: dict[str, str]) -> tuple[str, bytes, dict[str, Any]] | None:
    """Retrieve the linked species article's lead image for the detail card."""
    title = record["article_title"] or record["scientific_name"]
    filename = re.sub(r"[^a-z0-9]+", "-", record["id"].lower()).strip("-")
    return wikipedia_image(
        title,
        f"images/species/{filename}",
        subject=record["id"],
        kind="species",
    )


def genera() -> list[str]:
    """Return every genus in the display hierarchy in a stable order."""
    return [
        genus
        for subfamilies in TAXONOMY.values()
        for tribes in subfamilies.values()
        for genera_in_tribe in tribes.values()
        for genus in genera_in_tribe
    ]


def archive_readme(revision: dict[str, Any]) -> str:
    """Describe the contents and provenance of the generated archive."""
    return "\n".join([
        "# Cervidae example data",
        "",
        "This is a frozen snapshot for `examples/16_Cervidae_Tree.ipynb`.",
        "",
        f"Wikipedia revision: {revision['revision_id']} ({revision['timestamp']})",
        "Source: https://en.wikipedia.org/wiki/List_of_cervids",
        "",
        "`source/list_of_cervids.wikitext` preserves the source table.",
        "`taxonomy.json` is the compact hierarchy rendered by the notebook.",
        "`species.json` contains the 55 structured species records used by the details panel.",
        "`images/metadata.json` records Commons attribution and licenses for genus and species images.",
        "",
    ])


def build_archive(destination: Path) -> None:
    """Download the snapshot into an atomically replaced ZIP archive."""
    revision = wikipedia_revision()
    source_html = wikipedia_html(revision["revision_id"])
    species = species_records(source_html)
    image_metadata: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)
        archive_path = temporary_path / destination.name
        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr("README.md", archive_readme(revision))
            archive.writestr("taxonomy.json", json.dumps(TAXONOMY, indent=2) + "\n")
            archive.writestr(
                "source/list_of_cervids.json",
                json.dumps(
                    {
                        key: value
                        for key, value in revision.items()
                        if key != "wikitext"
                    },
                    indent=2,
                )
                + "\n",
            )
            archive.writestr("source/list_of_cervids.wikitext", revision["wikitext"])
            archive.writestr("source/list_of_cervids.html", source_html)
            archive.writestr("species.json", json.dumps(species, indent=2) + "\n")
            for genus in genera():
                result = genus_image(genus)
                if result is None:
                    continue
                name, image, metadata = result
                archive.writestr(name, image)
                image_metadata.append(metadata)
            for record in species:
                result = species_image(record)
                if result is not None:
                    name, image, metadata = result
                    archive.writestr(name, image)
                    image_metadata.append(metadata)
                range_result = wikipedia_image(
                    record["article_title"] or record["scientific_name"],
                    f"images/ranges/{re.sub(r'[^a-z0-9]+', '-', record['id'].lower())}",
                    subject=record["id"],
                    kind="range",
                )
                if range_result is not None:
                    name, image, metadata = range_result
                    archive.writestr(name, image)
                    image_metadata.append(metadata)
            archive.writestr(
                "images/metadata.json", json.dumps(image_metadata, indent=2) + "\n"
            )
            archive.writestr("images/review.json", "{}\n")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive_path, destination)


def parse_args() -> argparse.Namespace:
    """Parse the optional destination argument."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ARCHIVE)
    parser.add_argument(
        "--add-range-maps",
        action="store_true",
        help="Add maps to the existing archive while retaining reviewed images",
    )
    return parser.parse_args()


def add_range_maps(destination: Path) -> None:
    """Enrich an existing snapshot without changing any reviewed image bytes."""
    with zipfile.ZipFile(destination) as original:
        metadata = json.loads(original.read("images/metadata.json"))
        source = json.loads(original.read("source/list_of_cervids.json"))
        records = species_records(
            original.read("source/list_of_cervids.html").decode("utf-8")
        )
        known = {item["subject"] for item in metadata if item.get("kind") == "range"}
        additions = []
        for record in records:
            if record["id"] in known or not record["range_file"]:
                continue
            print(f"Fetching range map: {record['common_name']}", flush=True)
            stem = re.sub(r"[^a-z0-9]+", "-", record["id"].lower())
            result = commons_image(
                record["range_file"],
                f"images/ranges/{stem}",
                record["id"],
                "range",
                ("List of cervids", source["revision_id"]),
            )
            if result is not None:
                additions.append(result)
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            replacement = Path(temporary) / destination.name
            with zipfile.ZipFile(
                replacement, "w", compression=zipfile.ZIP_DEFLATED
            ) as updated:
                for entry in original.infolist():
                    if entry.filename != "images/metadata.json":
                        updated.writestr(entry, original.read(entry.filename))
                for name, content, item in additions:
                    updated.writestr(name, content)
                    metadata.append(item)
                updated.writestr(
                    "images/metadata.json", json.dumps(metadata, indent=2) + "\n"
                )
            original.close()
            shutil.copyfile(replacement, destination)
    print(f"Added {len(additions)} range maps; existing photo bytes preserved.")


if __name__ == "__main__":
    args = parse_args()
    if args.add_range_maps:
        add_range_maps(args.output)
    else:
        build_archive(args.output)
