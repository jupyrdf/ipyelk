# Cervidae example data

`cervidae-tree.zip` is a snapshot produced by
[`scripts/snapshot_cervidae.py`](../../scripts/snapshot_cervidae.py). It contains the
exact Wikipedia revision, the compact taxonomy, structured records for all 55 listed
species, a representative Commons image for every genus, and image attribution metadata.

User-supplied species photos are stored unchanged under `images/user/`, including Artist
alternatives and unmatched files. `images/user/import.json` records the mapping results.
Regular photos are preferred, genus nodes are text-only, and unmatched species stay
text-only. User-photo redistribution licenses have not been supplied; do not assume
these files share the Commons images' licenses.

The ZIP is tracked with Git LFS to keep the repository history small. Rebuild it only
when deliberately updating the example's source snapshot.

## Review photos and maps

Run `pixi run -e dev python scripts/review_cervidae_images.py` from the repository root,
then open `build/cervidae-image-review.html` in your browser. It embeds the archive's
images, works offline, and links to each Commons attribution page.

Classify each image as a deer photo, range map, or omitted. Drag over an image to select
a crop; **Use whole image** resets it. **Export review JSON** downloads
`cervidae-image-review.json`. Embed that export in the snapshot with:

```sh
pixi run -e dev python scripts/review_cervidae_images.py --import-review path/to/cervidae-image-review.json
```

The notebook and editor read `images/review.json` inside the LFS ZIP; the separate
export does not need to be committed. Rerun the notebook after importing. The notebook
applies those coordinates at display time; original image bytes remain unchanged.
Rebuild the editor to load saved choices, or import the JSON into an already open
editor. Export before closing the page.

Range maps are displayed separately from deer photographs. Filename-based map
classification in the downloader is a starting point and requires review.
