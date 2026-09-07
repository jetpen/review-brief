import json
from pathlib import Path

from review_brief_diagrams.handoff import validate_handoff


def write_manifest(tmp_path: Path, **overrides: object) -> Path:
    (tmp_path / "diagram.png").write_bytes(b"png")
    (tmp_path / "diagram.svg").write_text("<svg></svg>")
    manifest = {
        "contract": {"version": "1"},
        "generator": {"name": "test"},
        "input": {"source_sha256": "abc"},
        "diagram": {"family": "logical", "textual_description": "A diagram."},
        "configuration": {},
        "tools": {},
        "artifacts": [
            {"path": "diagram.png", "media_type": "image/png"},
            {"path": "diagram.svg", "media_type": "image/svg+xml"},
        ],
        "image": {"path": "diagram.png", "media_type": "image/png"},
        "diagnostics": [],
        "status": "succeeded",
    }
    manifest.update(overrides)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_successful_handoff_exposes_png_and_metadata(tmp_path: Path) -> None:
    result = validate_handoff(write_manifest(tmp_path))

    assert result.compatible
    assert result.status == "succeeded"
    assert result.png_path == tmp_path / "diagram.png"
    assert result.metadata["type"] == "logical"


def test_warning_status_remains_renderable(tmp_path: Path) -> None:
    result = validate_handoff(write_manifest(tmp_path, status="succeeded_with_warnings"))

    assert result.compatible
    assert result.status == "succeeded_with_warnings"
    assert result.warnings


def test_unsupported_contract_version_warns_and_is_incompatible(tmp_path: Path) -> None:
    result = validate_handoff(write_manifest(tmp_path, contract={"version": "99"}))

    assert not result.compatible
    assert any(d.category == "compatibility" for d in result.diagnostics)


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    result = validate_handoff(write_manifest(tmp_path, artifacts=[{"path": "../outside.png", "media_type": "image/png"}]))

    assert not result.compatible
    assert any(d.category == "path_safety" for d in result.diagnostics)


def test_active_svg_is_rejected(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path)
    (tmp_path / "diagram.svg").write_text('<svg><script>alert(1)</script></svg>')
    result = validate_handoff(manifest)

    assert not result.compatible
    assert any(d.category == "unsafe_svg" for d in result.diagnostics)


def test_failed_with_artifacts_does_not_expose_png_as_final(tmp_path: Path) -> None:
    result = validate_handoff(write_manifest(tmp_path, status="failed_with_artifacts"))

    assert result.status == "failed_with_artifacts"
    assert result.png_path is None
    assert result.compatible
