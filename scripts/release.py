"""Publish only distributions from a successful canonical CI run, without rebuilding."""

import argparse
import base64
import hashlib
import http
import io
import json
import os
import re
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import tomllib

REPO = "jupyrdf/ipyelk"
PACKAGE = "@jupyrdf/jupyter-elk"
REQUIRED = {
    "build",
    "build-cov",
    "lint",
    "docs",
    "test (ubuntu-latest)",
    "test (windows-latest)",
    "test (macos-latest)",
    "test-oldest (ubuntu-latest)",
    "test-oldest (windows-latest)",
    "test-oldest (macos-14)",
}


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def api(path):
    return json.loads(command("gh", "api", f"repos/{REPO}/{path}"))


def optional_api(path):
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/{path}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        if "(HTTP 404)" in result.stderr:
            return None
        raise RuntimeError(f"GitHub API request failed: {path}: {result.stderr}")
    return json.loads(result.stdout)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fetch_bytes(url):
    require(
        url.startswith("https://"), "Only HTTPS registry and asset URLs are allowed"
    )
    with urllib.request.build_opener().open(url, timeout=60) as response:
        return response.read()


def fetch_json(url):
    try:
        return json.loads(fetch_bytes(url))
    except urllib.error.HTTPError as error:
        if error.code == http.HTTPStatus.NOT_FOUND:
            return None
        raise


def versions(root=Path()):
    py = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:(a|b|rc)(\d+))?", py)
    require(
        match is not None, "Only explicit final, alpha, beta or RC versions publish"
    )
    suffix = {"a": "alpha", "b": "beta", "rc": "rc"}.get(match[2])
    npm = match[1] + (f"-{suffix}{match[3]}" if suffix else "")
    require(
        json.loads((root / "package.json").read_text())["version"] == npm,
        "Python and npm versions differ",
    )
    return py, npm, "next" if match[2] else "latest"


def validate_run(run, jobs, sha):
    require(run["repository"]["full_name"] == REPO, "Wrong CI repository")
    require(run["path"] == ".github/workflows/ci.yml", "Wrong CI workflow")
    require(run["event"] in {"push", "workflow_dispatch"}, "Untrusted CI event")
    require(run["head_branch"] == "master", "CI must qualify master")
    require(run["head_sha"] == sha, "CI commit does not match checkout")
    require(
        run["status"] == "completed" and run["conclusion"] == "success",
        "CI has not completed successfully",
    )
    require({job["name"] for job in jobs} == REQUIRED, "CI job set changed")
    require(
        all(job["conclusion"] == "success" for job in jobs),
        "Every required CI job must succeed",
    )


def validate_dist(dist, py, npm):
    expected = {
        f"ipyelk-{py}-py3-none-any.whl",
        f"ipyelk-{py}.tar.gz",
        f"jupyrdf-jupyter-elk-{npm}.tgz",
    }
    manifest = {}
    for line in (dist / "SHA256SUMS").read_text().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([^/\\]+)", line)
        require(match is not None, "Invalid checksum manifest line")
        digest, name = match.groups()
        require(name not in manifest, "Duplicate checksum entry")
        manifest[name] = digest
    require(
        set(manifest) == expected, "Manifest must contain exactly three distributions"
    )
    require(
        {p.name for p in dist.iterdir()} == expected | {"SHA256SUMS"},
        "Unexpected distribution files",
    )
    for name, digest in manifest.items():
        require(
            hashlib.sha256((dist / name).read_bytes()).hexdigest() == digest,
            f"Checksum mismatch: {name}",
        )
    with zipfile.ZipFile(dist / f"ipyelk-{py}-py3-none-any.whl") as wheel:
        metadata = wheel.read(f"ipyelk-{py}.dist-info/METADATA").decode()
        require(f"\nVersion: {py}\n" in metadata, "Wrong wheel version")
        ext = f"ipyelk-{py}.data/data/share/jupyter/labextensions/{PACKAGE}/"
        pkg = json.loads(wheel.read(ext + "package.json"))
        require(
            pkg["name"] == PACKAGE and pkg["version"] == npm, "Wrong bundled extension"
        )
        require(
            any(n.startswith(ext + "static/remoteEntry.") for n in wheel.namelist()),
            "Missing federated extension assets",
        )
    with tarfile.open(dist / f"jupyrdf-jupyter-elk-{npm}.tgz") as archive:
        pkg = json.load(archive.extractfile("package/package.json"))
        require(pkg["name"] == PACKAGE and pkg["version"] == npm, "Wrong npm tarball")
    with tarfile.open(dist / f"ipyelk-{py}.tar.gz") as archive:
        metadata = archive.extractfile(f"ipyelk-{py}/PKG-INFO").read().decode()
        require(f"\nVersion: {py}\n" in metadata, "Wrong sdist version")
    return manifest


def registry_state(dist, py, npm, *, write_pending=True):
    """Existing uploads are accepted only when their bytes match the tested files."""
    pypi = fetch_json(f"https://pypi.org/pypi/ipyelk/{py}/json")
    existing = (
        {item["filename"]: item["digests"]["sha256"] for item in pypi["urls"]}
        if pypi
        else {}
    )
    for name, digest in existing.items():
        require((dist / name).is_file(), f"Unexpected PyPI file: {name}")
        require(
            hashlib.sha256((dist / name).read_bytes()).hexdigest() == digest,
            f"Published PyPI bytes differ: {name}",
        )
    npm_data = fetch_json(f"https://registry.npmjs.org/@jupyrdf%2fjupyter-elk/{npm}")
    if npm_data:
        integrity = (
            "sha512-"
            + base64.b64encode(
                hashlib.sha512(
                    (dist / f"jupyrdf-jupyter-elk-{npm}.tgz").read_bytes()
                ).digest()
            ).decode()
        )
        require(
            npm_data["dist"].get("integrity") == integrity, "Published npm bytes differ"
        )
    missing = [
        file
        for file in [*dist.glob("*.whl"), *dist.glob("*.tar.gz")]
        if file.name not in existing
    ]
    if write_pending:
        pending = Path("pending-pypi")
        pending.mkdir(exist_ok=True)
        require(not list(pending.iterdir()), "Pending upload directory must be empty")
        for file in missing:
            (pending / file.name).write_bytes(file.read_bytes())
    return bool(npm_data), bool(missing)


def channel_matches(npm, channel):
    tags = fetch_json("https://registry.npmjs.org/@jupyrdf%2fjupyter-elk")
    return tags is not None and tags["dist-tags"].get(channel) == npm


def verify_channel(npm, channel):
    require(channel_matches(npm, channel), "Published npm channel differs")


def await_publication(dist, py, npm, channel):
    # Registries may expose a just-uploaded file after the upload call returns.
    attempts = 6
    for attempt in range(attempts):
        npm_exists, pypi_pending = registry_state(dist, py, npm, write_pending=False)
        if npm_exists and not pypi_pending and channel_matches(npm, channel):
            return
        if attempt + 1 < attempts:
            time.sleep(10)
    raise ValueError(
        "Publication not visible after 50 seconds; resume this same CI run"
    )


def github_state(dist, py, channel, sha):
    """Reject collisions before uploads; permit only missing GitHub assets on resume."""
    tag = f"v{py}"
    refs = api("git/matching-refs/tags/" + tag)
    exact = [ref for ref in refs if ref["ref"] == f"refs/tags/{tag}"]
    if exact:
        obj = exact[0]["object"]
        while obj["type"] == "tag":
            obj = api("git/tags/" + obj["sha"])["object"]
        require(obj["sha"] == sha, "Existing tag points to another commit")
    existing = optional_api(f"releases/tags/{tag}")
    if existing:
        require(bool(exact), "Release exists without its expected tag")
        require(existing["prerelease"] == (channel == "next"), "Wrong release channel")
        require(not existing["draft"], "Existing release is a draft")
        assets = {asset["name"]: asset for asset in existing["assets"]}
        require(
            set(assets) <= {p.name for p in dist.iterdir()}, "Unexpected release assets"
        )
        for name, asset in assets.items():
            require(
                fetch_bytes(asset["browser_download_url"])
                == (dist / name).read_bytes(),
                "Release asset bytes differ",
            )
    return bool(exact), existing


def finalize(dist, py, channel, sha, run):
    tag_exists, existing = github_state(dist, py, channel, sha)
    tag = f"v{py}"
    if not tag_exists:
        command(
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{REPO}/git/refs",
            "-f",
            f"ref=refs/tags/{tag}",
            "-f",
            f"sha={sha}",
        )
    if existing:
        names = {asset["name"] for asset in existing["assets"]}
        missing = [
            str(path) for path in sorted(dist.iterdir()) if path.name not in names
        ]
        if missing:
            command("gh", "release", "upload", tag, "--repo", REPO, *missing)
    else:
        command(
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            REPO,
            "--verify-tag",
            "--title",
            f"ipyelk {py}",
            "--notes",
            f"Qualified CI: {run['html_url']}\n\nSee CHANGELOG.md for migration and known limitations.",
            "--prerelease" if channel == "next" else "--latest",
            *map(str, sorted(dist.iterdir())),
        )
    _, complete = github_state(dist, py, channel, sha)
    require(
        complete is not None
        and {a["name"] for a in complete["assets"]} == {p.name for p in dist.iterdir()},
        "GitHub publication incomplete",
    )


def download_dist(run, dist, py, npm):
    artifacts = api(f"actions/runs/{run['id']}/artifacts?per_page=100")["artifacts"]
    matches = [
        item for item in artifacts if item["name"] == f"ipyelk-{run['run_number']}-dist"
    ]
    require(
        len(matches) == 1 and not matches[0]["expired"], "Missing immutable CI artifact"
    )
    artifact = matches[0]
    payload = subprocess.check_output([
        "gh",
        "api",
        f"repos/{REPO}/actions/artifacts/{artifact['id']}/zip",
    ])
    require(
        artifact.get("digest") == "sha256:" + hashlib.sha256(payload).hexdigest(),
        "CI artifact download digest differs",
    )
    allowed = {
        "SHA256SUMS",
        f"ipyelk-{py}-py3-none-any.whl",
        f"ipyelk-{py}.tar.gz",
        f"jupyrdf-jupyter-elk-{npm}.tgz",
    }
    require(not dist.exists(), "Artifact destination must be new")
    dist.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        files = [info for info in archive.infolist() if not info.is_dir()]
        selected = [info for info in files if info.filename.startswith("dist/")]
        require(
            {info.filename for info in selected} == {f"dist/{name}" for name in allowed}
            and len(selected) == len(allowed),
            "Unexpected or duplicate distribution archive paths",
        )
        # Copy only the four allowlisted direct children: never extract task caches or paths.
        for info in selected:
            (dist / info.filename.removeprefix("dist/")).write_bytes(archive.read(info))


def qualifying_run(run_id, sha):
    run = api(f"actions/runs/{run_id}")
    jobs = json.loads(
        command(
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100",
        )
    )
    validate_run(run, [job for page in jobs for job in page["jobs"]], sha)
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "finish"])
    parser.add_argument("--run-id", required=True, type=int)
    args = parser.parse_args()
    sha = command("git", "rev-parse", "HEAD")
    run = qualifying_run(args.run_id, sha)
    py, npm, channel = versions()
    require(
        tomllib.loads(command("git", "show", "HEAD^:pyproject.toml"))["project"][
            "version"
        ]
        != py,
        "Only a commit changing the release version may publish",
    )
    dist = Path("release-artifact/dist")
    if args.mode == "prepare":
        download_dist(run, dist, py, npm)
    validate_dist(dist, py, npm)
    github_state(dist, py, channel, sha)
    if args.mode == "prepare":
        npm_exists, pypi_pending = registry_state(dist, py, npm)
        if npm_exists:
            verify_channel(npm, channel)
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(
                f"python={py}\nnpm={npm}\nchannel={channel}\n"
                f"npm_exists={str(npm_exists).lower()}\n"
                f"pypi_pending={str(pypi_pending).lower()}\n"
            )
    else:
        await_publication(dist, py, npm, channel)
        finalize(dist, py, channel, sha, run)


if __name__ == "__main__":
    main()
