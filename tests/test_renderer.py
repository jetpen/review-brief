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


def test_manifest_records_reproducibility_metadata(tmp_path: Path) -> None:
    bundle = render_request(write_request(tmp_path, VALID_MERMAID))
    manifest = json.loads((bundle.path / "manifest.json").read_text())

    assert manifest["contract"]["mermaid_subset_version"] == "1"
    assert manifest["contract"]["ir_schema_version"] == "1"
    assert manifest["generator"]["generated_at"].endswith("+00:00")
    assert manifest["generator"]["run_id"]
    assert manifest["diagram"]["semantic_metadata"]["node_ids"] == ["api", "db"]
    assert manifest["image"]["aspect_ratio"] > 0


def test_logical_roles_and_shapes_survive_dot_generation() -> None:
    from review_brief_diagrams.renderer import parse_logical_flowchart, to_dot

    ir = parse_logical_flowchart('flowchart LR\napi["[service] API"] --> db[("[data_store] Database")]\n')
    dot = to_dot(ir)

    assert 'shape="cylinder"' in dot
    assert 'comment="role:data_store"' in dot
    assert 'comment="role:service"' in dot


def test_empty_flowchart_is_semantic_failure() -> None:
    from review_brief_diagrams.renderer import RenderError, parse_logical_flowchart

    with pytest.raises(RenderError) as exc_info:
        parse_logical_flowchart("flowchart LR\n")

    assert exc_info.value.exit_code == 3
    assert exc_info.value.diagnostic["category"] == "semantic_validation"


def test_cli_returns_structured_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from review_brief_diagrams import cli

    request = write_request(tmp_path, VALID_MERMAID)
    payload = json.loads(request.read_text())
    payload["diagram"]["family"] = "deployment"
    request.write_text(json.dumps(payload))

    assert cli.main([str(request)]) == 2
    assert json.loads(capsys.readouterr().err)["error"]["category"] == "invalid_request"


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
