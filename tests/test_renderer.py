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
    assert 'shape="box"' in dot
    assert ir.nodes[0].role == "service"
    assert ir.nodes[1].role == "data_store"


def test_empty_flowchart_is_semantic_failure() -> None:
    from review_brief_diagrams.renderer import RenderError, parse_logical_flowchart

    with pytest.raises(RenderError) as exc_info:
        parse_logical_flowchart("flowchart LR\n")

    assert exc_info.value.exit_code == 3
    assert exc_info.value.diagnostic["category"] == "semantic_validation"


def test_roles_relationships_and_containers_render(tmp_path: Path) -> None:
    from review_brief_diagrams.renderer import parse_logical_flowchart, to_dot

    source = '''flowchart LR
subgraph core["Core"]
  api["[service] API"] -->|[calls]| auth["[service] Auth"]
end
'''
    ir = parse_logical_flowchart(source)
    dot = to_dot(ir)

    assert ir.containers[0].id == "core"
    assert ir.nodes[0].container_id == "core"
    assert ir.edges[0].role == "calls"
    assert 'cluster_core' in dot
    assert 'comment="role:calls"' in dot


def test_deployment_role_fails_in_logical_family() -> None:
    from review_brief_diagrams.renderer import RenderError, parse_logical_flowchart

    with pytest.raises(RenderError) as exc_info:
        parse_logical_flowchart('flowchart LR\napi["[workload] API"]\n')

    assert exc_info.value.exit_code == 3
    assert exc_info.value.diagnostic["category"] == "semantic_validation"


def test_style_profile_is_recorded_and_validated(tmp_path: Path) -> None:
    request = write_request(tmp_path, VALID_MERMAID)
    payload = json.loads(request.read_text())
    payload["rendering"] = {"style_profile": {"name": "brand-blue", "version": "1", "node_fill": "#e0f2fe", "background": "#ffffff"}}
    request.write_text(json.dumps(payload))

    bundle = render_request(request)
    manifest = json.loads((bundle.path / "manifest.json").read_text())
    assert manifest["configuration"]["style_profile"]["name"] == "brand-blue"
    assert manifest["configuration"]["style_profile"]["node_fill"] == "#e0f2fe"


def test_low_contrast_style_profile_is_rejected(tmp_path: Path) -> None:
    request = write_request(tmp_path, VALID_MERMAID)
    payload = json.loads(request.read_text())
    payload["rendering"] = {"style_profile": {"name": "bad", "version": "1", "text_color": "#aaaaaa", "background": "#ffffff"}}
    request.write_text(json.dumps(payload))

    with pytest.raises(RenderError) as exc_info:
        render_request(request)

    assert exc_info.value.exit_code == 2
    assert exc_info.value.diagnostic["category"] == "style_validation"


def test_deployment_flowchart_renders_network_metadata(tmp_path: Path) -> None:
    request = write_request(tmp_path, '''flowchart TB
subgraph prod["[deployment] Production"]
  api["[workload] API"] -->|[network_flow][HTTPS:443][ingress]| db["[database] Database"]
end
''')
    payload = json.loads(request.read_text())
    payload["diagram"]["family"] = "deployment"
    request.write_text(json.dumps(payload))

    bundle = render_request(request)
    manifest = json.loads((bundle.path / "manifest.json").read_text())
    ir = json.loads((bundle.path / "ir.json").read_text())
    assert manifest["diagram"]["family"] == "deployment"
    assert manifest["diagram"]["direction"] == "TB"
    assert ir["containers"][0]["role"] == "deployment"
    assert ir["edges"][0]["role"] == "ingress"


def test_logical_request_rejects_deployment_role(tmp_path: Path) -> None:
    with pytest.raises(RenderError) as exc_info:
        render_request(write_request(tmp_path, 'flowchart LR\napi["[workload] API"]\n'))
    assert exc_info.value.exit_code == 3


def test_interaction_sequence_renders_ordered_messages(tmp_path: Path) -> None:
    from review_brief_diagrams.renderer import parse_sequence_diagram, to_dot

    ir = parse_sequence_diagram('''sequenceDiagram
actor User
participant API as "[service] API"
participant DB as "[database] DB"
User->>API: [request] Submit
API-->>User: [response] Accepted
API-)DB: [event] Stored
''')
    dot = to_dot(ir)

    assert [edge.sequence_index for edge in ir.edges] == [1, 2, 3]
    assert [edge.role for edge in ir.edges] == ["request", "response", "event"]
    assert 'xlabel="1"' in dot
    assert 'style="dashed"' in dot


def test_interaction_activation_and_unsupported_constructs() -> None:
    from review_brief_diagrams.renderer import RenderError, parse_sequence_diagram

    with pytest.raises(RenderError) as activation_error:
        parse_sequence_diagram('sequenceDiagram\nparticipant API\nactivate API\nAPI->>API: work\n')
    assert activation_error.value.diagnostic["category"] == "invalid_syntax"

    with pytest.raises(RenderError) as unsupported_error:
        parse_sequence_diagram('sequenceDiagram\nparticipant API\nparticipant DB\nloop retry\nAPI->>DB: work\nend\n')
    assert unsupported_error.value.diagnostic["category"] == "unsupported_syntax"


def test_cli_direct_mode_renders_without_json_request(tmp_path: Path) -> None:
    from review_brief_diagrams import cli

    source = tmp_path / "direct.mmd"
    source.write_text(VALID_MERMAID)
    assert cli.main(["--source", str(source), "--family", "logical", "--output", str(tmp_path / "bundle")]) == 0
    assert (tmp_path / "bundle" / "diagram.png").is_file()


def test_cli_requires_named_request_qualifier(tmp_path: Path) -> None:
    from review_brief_diagrams import cli

    with pytest.raises(SystemExit):
        cli.main([str(tmp_path / "request.json")])


def test_cli_returns_structured_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from review_brief_diagrams import cli

    request = write_request(tmp_path, VALID_MERMAID)
    payload = json.loads(request.read_text())
    payload["diagram"]["family"] = "deployment"
    request.write_text(json.dumps(payload))

    assert cli.main(["--request", str(request)]) == 3
    assert json.loads(capsys.readouterr().err)["error"]["category"] == "semantic_validation"


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

    assert exc_info.value.exit_code == 3
    assert exc_info.value.diagnostic["category"] == "semantic_validation"


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
