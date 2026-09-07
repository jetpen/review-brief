from pathlib import Path

import json

import pytest

from review_brief_diagrams.renderer import RenderError, render_request


VALID_MERMAID = """flowchart LR
  api[API] --> db[(Database)]
"""


def write_request(tmp_path: Path, source: str, **overrides: object) -> Path:
    source_path = tmp_path / "architecture.mmd"
    source_path.write_text(source, encoding="utf-8")
    request: dict[str, object] = {
        "source": {"path": source_path.name},
        "diagram": {"family": "logical"},
        "output": {"bundle_dir": "bundle"},
    }
    for key, value in overrides.items():
        request[key] = value
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    return request_path


def test_logical_flowchart_creates_complete_bundle(tmp_path: Path) -> None:
    bundle = render_request(write_request(tmp_path, VALID_MERMAID))

    assert [path.name for path in bundle.artifacts] == [
        "source.mmd",
        "ir.json",
        "diagram.dot",
        "diagram.svg",
        "diagram.png",
        "manifest.json",
    ]
    manifest = json.loads((bundle.path / "manifest.json").read_text())
    assert manifest["status"] == "succeeded"
    assert manifest["diagram"]["family"] == "logical"
    assert manifest["image"]["media_type"] == "image/png"
    assert manifest["image"]["width"] > 0
    assert manifest["image"]["height"] > 0
    assert all(item["sha256"] for item in manifest["artifacts"])


def test_relative_paths_resolve_from_request_directory(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    request = write_request(nested, VALID_MERMAID)

    bundle = render_request(request)

    assert bundle.path == nested / "bundle"


def test_invalid_diagram_family_fails_with_stable_exit_code(tmp_path: Path) -> None:
    request = write_request(tmp_path, VALID_MERMAID)
    payload = json.loads(request.read_text())
    payload["diagram"]["family"] = "deployment"
    request.write_text(json.dumps(payload))

    with pytest.raises(RenderError) as exc_info:
        render_request(request)

    assert exc_info.value.exit_code == 2
    assert exc_info.value.diagnostic["category"] == "invalid_request"


def test_unsupported_mermaid_syntax_fails_with_stable_exit_code(tmp_path: Path) -> None:
    request = write_request(tmp_path, "sequenceDiagram\n  A->>B: hello\n")

    with pytest.raises(RenderError) as exc_info:
        render_request(request)

    assert exc_info.value.exit_code == 2
    assert exc_info.value.diagnostic["category"] == "unsupported_syntax"


def test_existing_bundle_is_not_overwritten_without_flag(tmp_path: Path) -> None:
    request = write_request(tmp_path, VALID_MERMAID)
    render_request(request)
    with pytest.raises(RenderError) as exc_info:
        render_request(request)

    assert exc_info.value.exit_code == 5
    assert exc_info.value.diagnostic["category"] == "filesystem"


def test_missing_source_has_structured_diagnostic(tmp_path: Path) -> None:
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "source": {"path": "missing.mmd"},
                "diagram": {"family": "logical"},
                "output": {"bundle_dir": "bundle"},
            }
        )
    )

    with pytest.raises(RenderError) as exc_info:
        render_request(request)

    assert exc_info.value.exit_code == 5
    assert exc_info.value.diagnostic["severity"] == "error"
