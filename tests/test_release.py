"""Fail closed at release provenance and immutable artifact boundaries."""

import hashlib
import importlib.util
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "release", Path(__file__).parents[1] / "scripts/release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def valid_run():
    return {
        "repository": {"full_name": release.REPO},
        "path": ".github/workflows/ci.yml",
        "event": "push",
        "head_branch": "master",
        "head_sha": "abc",
        "status": "completed",
        "conclusion": "success",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event", "pull_request"),
        ("head_branch", "feature"),
        ("head_sha", "other"),
        ("conclusion", "failure"),
        ("path", ".github/workflows/other.yml"),
    ],
)
def test_unqualified_runs_rejected(field, value):
    run = valid_run()
    run[field] = value
    with pytest.raises(ValueError, match=r".+"):
        release.validate_run(
            run, [{"name": n, "conclusion": "success"} for n in release.REQUIRED], "abc"
        )


def test_required_jobs_must_all_execute():
    jobs = [{"name": n, "conclusion": "success"} for n in release.REQUIRED]
    release.validate_run(valid_run(), jobs, "abc")
    with pytest.raises(ValueError, match=r".+"):
        release.validate_run(valid_run(), jobs[:-1], "abc")
    jobs[0]["conclusion"] = "skipped"
    with pytest.raises(ValueError, match=r".+"):
        release.validate_run(valid_run(), jobs, "abc")


def test_version_mapping(tmp_path):
    for py, npm, channel in [
        ("3.0.0", "3.0.0", "latest"),
        ("3.0.0rc1", "3.0.0-rc1", "next"),
    ]:
        (tmp_path / "pyproject.toml").write_text(f'[project]\nversion = "{py}"\n')
        (tmp_path / "package.json").write_text(json.dumps({"version": npm}))
        assert release.versions(tmp_path) == (py, npm, channel)
    (tmp_path / "package.json").write_text('{"version":"3.0.0-rc.1"}')
    with pytest.raises(ValueError, match=r".+"):
        release.versions(tmp_path)


def distributions(path):
    package = json.dumps({"name": release.PACKAGE, "version": "3.0.0"}).encode()
    with zipfile.ZipFile(path / "ipyelk-3.0.0-py3-none-any.whl", "w") as archive:
        archive.writestr(
            "ipyelk-3.0.0.dist-info/METADATA", "Name: ipyelk\nVersion: 3.0.0\n"
        )
        prefix = (
            "ipyelk-3.0.0.data/data/share/jupyter/labextensions/@jupyrdf/jupyter-elk/"
        )
        archive.writestr(prefix + "package.json", package)
        archive.writestr(prefix + "static/remoteEntry.hash.js", "bundle")
    for name, member, content in [
        (
            "ipyelk-3.0.0.tar.gz",
            "ipyelk-3.0.0/PKG-INFO",
            b"Name: ipyelk\nVersion: 3.0.0\n",
        ),
        ("jupyrdf-jupyter-elk-3.0.0.tgz", "package/package.json", package),
    ]:
        with tarfile.open(path / name, "w:gz") as archive:
            info = tarfile.TarInfo(member)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    (path / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
            for p in sorted(path.iterdir())
        )
    )


def test_distribution_bytes_and_manifest_rejected(tmp_path):
    distributions(tmp_path)
    release.validate_dist(tmp_path, "3.0.0", "3.0.0")
    wheel = tmp_path / "ipyelk-3.0.0-py3-none-any.whl"
    wheel.write_bytes(wheel.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        release.validate_dist(tmp_path, "3.0.0", "3.0.0")


def test_registry_mismatch_never_becomes_skip(tmp_path, monkeypatch):
    distributions(tmp_path)
    monkeypatch.setattr(
        release,
        "fetch_json",
        lambda _url: {
            "urls": [
                {"filename": "ipyelk-3.0.0.tar.gz", "digests": {"sha256": "wrong"}}
            ]
        },
    )
    with pytest.raises(ValueError, match="Published PyPI bytes differ"):
        release.registry_state(tmp_path, "3.0.0", "3.0.0")


@pytest.mark.parametrize(
    ("py", "npm"), [("3.0.0a1", "3.0.0-alpha1"), ("3.0.0b2", "3.0.0-beta2")]
)
def test_widget_prerelease_mapping(tmp_path, py, npm):
    (tmp_path / "pyproject.toml").write_text(f'[project]\nversion = "{py}"\n')
    (tmp_path / "package.json").write_text(json.dumps({"version": npm}))
    assert release.versions(tmp_path) == (py, npm, "next")


def test_tag_collision_rejected_before_registry_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(
        release,
        "api",
        lambda _path: [
            {"ref": "refs/tags/v3.0.0", "object": {"type": "commit", "sha": "other"}}
        ],
    )
    with pytest.raises(ValueError, match="Existing tag points to another commit"):
        release.github_state(tmp_path, "3.0.0", "latest", "intended")


def test_partial_github_upload_only_adds_missing_files(tmp_path, monkeypatch):
    distributions(tmp_path)
    existing = {"assets": [{"name": "SHA256SUMS"}]}
    states = iter([
        (True, existing),
        (True, {"assets": [{"name": p.name} for p in tmp_path.iterdir()]}),
    ])
    monkeypatch.setattr(release, "github_state", lambda *_args: next(states))
    commands = []
    monkeypatch.setattr(release, "command", lambda *args: commands.append(args))
    release.finalize(tmp_path, "3.0.0", "latest", "intended", {"html_url": "CI"})
    assert len(commands) == 1
    assert commands[0][:4] == ("gh", "release", "upload", "v3.0.0")
    assert not any("SHA256SUMS" in arg for arg in commands[0])
    assert len(commands[0]) == 9


def test_archive_never_extracts_unapproved_paths(tmp_path, monkeypatch):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("dist/../../escape", "malicious")
    content = payload.getvalue()
    monkeypatch.setattr(
        release,
        "api",
        lambda _path: {
            "artifacts": [
                {
                    "name": "ipyelk-1-dist",
                    "id": 2,
                    "expired": False,
                    "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
                }
            ]
        },
    )
    monkeypatch.setattr(release.subprocess, "check_output", lambda _args: content)
    with pytest.raises(
        ValueError, match="Unexpected or duplicate distribution archive paths"
    ):
        release.download_dist(
            {"id": 1, "run_number": 1}, tmp_path / "dist", "3.0.0", "3.0.0"
        )
    assert not (tmp_path / "escape").exists()


def test_registry_visibility_is_bounded_and_can_resume(tmp_path, monkeypatch):
    states = iter([(False, True), (True, True), (True, False)])
    monkeypatch.setattr(release, "registry_state", lambda *_a, **_kw: next(states))
    sleeps = []
    monkeypatch.setattr(release.time, "sleep", sleeps.append)
    channels = []
    monkeypatch.setattr(
        release, "channel_matches", lambda *args: channels.append(args) or True
    )
    release.await_publication(tmp_path, "3.0.0", "3.0.0", "latest")
    assert sleeps == [10, 10]
    assert channels == [("3.0.0", "latest")]
    monkeypatch.setattr(release, "registry_state", lambda *_a, **_kw: (False, True))
    sleeps.clear()
    with pytest.raises(ValueError, match="Publication not visible after 50 seconds"):
        release.await_publication(tmp_path, "3.0.0", "3.0.0", "latest")
    assert sleeps == [10] * 5


def test_registry_identical_partial_upload_only_copies_missing_file(
    tmp_path, monkeypatch
):
    dist = tmp_path / "dist"
    dist.mkdir()
    distributions(dist)
    wheel = dist / "ipyelk-3.0.0-py3-none-any.whl"
    monkeypatch.chdir(tmp_path)
    data = iter([
        {
            "urls": [
                {
                    "filename": wheel.name,
                    "digests": {
                        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()
                    },
                }
            ]
        },
        None,
    ])
    monkeypatch.setattr(release, "fetch_json", lambda _url: next(data))
    assert release.registry_state(dist, "3.0.0", "3.0.0") == (False, True)
    assert [p.name for p in (tmp_path / "pending-pypi").iterdir()] == [
        "ipyelk-3.0.0.tar.gz"
    ]


def test_visibility_waits_for_channel_without_republishing(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "registry_state", lambda *_a, **_kw: (True, False))
    states = iter([False, True])
    monkeypatch.setattr(release, "channel_matches", lambda *_a: next(states))
    sleeps = []
    monkeypatch.setattr(release.time, "sleep", sleeps.append)
    release.await_publication(tmp_path, "3.0.0", "3.0.0", "latest")
    assert sleeps == [10]
