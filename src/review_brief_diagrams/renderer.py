from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ArtifactBundle, DiagramIR, Edge, Node

CONTRACT_VERSION = "1"
EXIT_INVALID = 2
EXIT_TRANSFORM = 3
EXIT_GRAPHVIZ = 4
EXIT_FILESYSTEM = 5
EXIT_INTERNAL = 6
FLOWCHART_RE = re.compile(r"^\s*flowchart(?:\s+(?P<direction>TB|TD|BT|RL|LR))?\s*$")
EDGE_OPERATOR_RE = re.compile(r"(-->|---|-.->|==>|-\\.-)")
ROLE_RE = re.compile(r"^\[(?P<role>[a-z_]+)\]\s*(?P<label>.*)$")
LOGICAL_ROLES = {"system", "component", "service", "interface", "data_store", "external_actor", "external_system", "library", "boundary"}


def _split_edge(line: str) -> tuple[str, str, str | None, str] | None:
    quote = False
    depth = 0
    index = 0
    while index < len(line):
        char = line[index]
        if char == '"':
            quote = not quote
        elif not quote and char in "[({":
            depth += 1
        elif not quote and char in "]) }".replace(" ", ""):
            depth = max(0, depth - 1)
        elif not quote and depth == 0:
            match = EDGE_OPERATOR_RE.match(line, index)
            if match:
                left = line[:index].strip()
                right = line[match.end():].strip()
                label = None
                if right.startswith("|"):
                    end = right.find("|", 1)
                    if end < 0:
                        return None
                    label = right[1:end]
                    right = right[end + 1:].strip()
                return left, match.group(1), label, right
        index += 1
    return None


def _split_role(label: str) -> tuple[str, str | None]:
    match = ROLE_RE.match(label.strip())
    if not match:
        return label.strip(), None
    role = match.group("role")
    if role not in LOGICAL_ROLES:
        return label.strip(), None
    return match.group("label").strip() or role, role
ENDPOINT_RE = re.compile(r"^(?P<id>[A-Za-z_][\w-]*)(?P<body>.*)$")


def _parse_endpoint(token: str) -> tuple[str, str, str]:
    match = ENDPOINT_RE.match(token.strip())
    if not match:
        raise RenderError(f"invalid node endpoint: {token}", EXIT_INVALID, "invalid_syntax", "parse")
    node_id = match.group("id")
    body = match.group("body")
    if not body:
        return node_id, node_id, "["
    pairs = {
        "[(": ("[(", ")]", "cylinder"),
        "((": ("((", "))", "circle"),
        "[": ("[", "]", "box"),
        "(": ("(", ")", "ellipse"),
        "{": ("{", "}", "diamond"),
    }
    for opening, (prefix, suffix, shape) in pairs.items():
        if body.startswith(prefix) and body.endswith(suffix):
            label = body[len(prefix) : -len(suffix)]
            if label.startswith('"') and label.endswith('"'):
                label = label[1:-1]
            return node_id, label.strip() or node_id, shape
    raise RenderError(f"invalid node endpoint: {token}", EXIT_INVALID, "invalid_syntax", "parse")


def _shape_name(shape: str) -> str:
    return {"cylinder": "cylinder", "box": "box", "ellipse": "ellipse", "diamond": "diamond", "circle": "circle", "[(": "cylinder", "[": "box", "(": "ellipse", "{": "diamond", "((": "circle"}.get(shape, "box")


class RenderError(Exception):
    def __init__(self, message: str, exit_code: int, category: str, phase: str = "validation") -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.diagnostic = {
            "phase": phase,
            "category": category,
            "severity": "error",
            "message": message,
            "remediation": "Correct the request or Mermaid source and retry.",
        }


def render_request(request_path: str | Path) -> ArtifactBundle:
    request_file = Path(request_path).resolve()
    try:
        request = json.loads(request_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RenderError(str(exc), EXIT_FILESYSTEM, "filesystem", "request") from exc

    source_path, bundle_path, family = _validate_request(request, request_file.parent)
    if bundle_path.exists():
        raise RenderError(
            f"artifact bundle already exists: {bundle_path}", EXIT_FILESYSTEM, "filesystem", "request"
        )
    try:
        source_bytes = source_path.read_bytes()
        source_text = source_bytes.decode("utf-8")
        ir = parse_logical_flowchart(source_text)
    except RenderError:
        raise
    except (OSError, UnicodeDecodeError) as exc:
        raise RenderError(str(exc), EXIT_FILESYSTEM, "filesystem", "source") from exc

    temp_path = Path(tempfile.mkdtemp(prefix=f".{bundle_path.name}.", dir=bundle_path.parent))
    try:
        (temp_path / "source.mmd").write_bytes(source_bytes)
        (temp_path / "ir.json").write_text(json.dumps(ir.as_dict(), indent=2) + "\n", encoding="utf-8")
        dot_text = to_dot(ir)
        (temp_path / "diagram.dot").write_text(dot_text, encoding="utf-8")
        _run_graphviz(temp_path / "diagram.dot", temp_path / "diagram.svg", temp_path / "diagram.png")
        manifest = _make_manifest(temp_path, ir, source_bytes, family)
        (temp_path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        temp_path.rename(bundle_path)
    except RenderError:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise
    except OSError as exc:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise RenderError(str(exc), EXIT_FILESYSTEM, "filesystem", "artifact") from exc
    except Exception as exc:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise RenderError(str(exc), EXIT_INTERNAL, "internal", "render") from exc

    return ArtifactBundle(bundle_path, tuple(bundle_path / name for name in _artifact_names()))


def _validate_request(request: Any, base_dir: Path) -> tuple[Path, Path, str]:
    if not isinstance(request, dict):
        raise RenderError("request must be a JSON object", EXIT_INVALID, "invalid_request", "request")
    source = request.get("source")
    diagram = request.get("diagram")
    output = request.get("output")
    if not isinstance(source, dict) or not isinstance(diagram, dict) or not isinstance(output, dict):
        raise RenderError("source, diagram, and output objects are required", EXIT_INVALID, "invalid_request", "request")
    source_value = source.get("path")
    bundle_value = output.get("bundle_dir")
    family = diagram.get("family")
    if not isinstance(source_value, str) or not isinstance(bundle_value, str):
        raise RenderError("source.path and output.bundle_dir must be strings", EXIT_INVALID, "invalid_request", "request")
    if family != "logical":
        raise RenderError("minimal tracer bullet supports only the logical family", EXIT_INVALID, "invalid_request", "request")
    source_path = Path(source_value)
    bundle_path = Path(bundle_value)
    if not source_path.is_absolute():
        source_path = base_dir / source_path
    if not bundle_path.is_absolute():
        bundle_path = base_dir / bundle_path
    if not source_path.is_file():
        raise RenderError(f"source file does not exist: {source_path}", EXIT_FILESYSTEM, "filesystem", "source")
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    return source_path, bundle_path, family


def parse_logical_flowchart(source: str) -> DiagramIR:
    lines = [line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("%%")]
    if not lines or FLOWCHART_RE.match(lines[0]) is None:
        raise RenderError("expected a flowchart declaration", EXIT_INVALID, "unsupported_syntax", "parse")
    direction_match = FLOWCHART_RE.match(lines[0])
    assert direction_match is not None
    direction = direction_match.group("direction") or "LR"
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    for line_number, line in enumerate(lines[1:], start=2):
        edge_parts = _split_edge(line)
        if edge_parts:
            source_token, operator, edge_label, target_token = edge_parts
            source_id, source_label, source_shape = _parse_endpoint(source_token)
            target_id, target_label, target_shape = _parse_endpoint(target_token)
            source_label, source_role = _split_role(source_label)
            target_label, target_role = _split_role(target_label)
            nodes.setdefault(source_id, Node(source_id, source_label, _shape_name(source_shape), source_role))
            nodes.setdefault(target_id, Node(target_id, target_label, _shape_name(target_shape), target_role))
            edges.append(
                Edge(
                    id=f"edge-{len(edges) + 1}",
                    source=source_id,
                    target=target_id,
                    label=edge_label,
                    directed=operator != "---",
                    style="dashed" if "-." in operator else "solid",
                )
            )
            continue
        try:
            node_id, label, shape = _parse_endpoint(line.strip())
        except RenderError:
            raise RenderError(f"unsupported Mermaid syntax on line {line_number}", EXIT_INVALID, "unsupported_syntax", "parse")
        label, role = _split_role(label)
        if node_id in nodes and nodes[node_id].label != node_id and nodes[node_id].label != label:
            raise RenderError(f"duplicate node declaration: {node_id}", EXIT_INVALID, "invalid_syntax", "parse")
        nodes[node_id] = Node(node_id, label, _shape_name(shape), role)
    if not nodes:
        raise RenderError("flowchart contains no nodes", EXIT_TRANSFORM, "semantic_validation", "validate")
    return DiagramIR("logical", direction, tuple(nodes.values()), tuple(edges))


def to_dot(ir: DiagramIR) -> str:
    direction = {"TB": "TB", "TD": "TB", "BT": "BT", "RL": "RL", "LR": "LR"}[ir.direction]
    lines = [
        "digraph review_brief {",
        f'  rankdir="{direction}";',
        '  graph [bgcolor="#ffffff", pad="0.35", nodesep="0.55", ranksep="0.8", splines="polyline", outputorder="edgesfirst"];',
        '  node [fontname="DejaVu Sans", fontsize=11, style="rounded,filled", color="#334155", fontcolor="#0f172a", fillcolor="#dbeafe", margin="0.16,0.10"];',
        '  edge [fontname="DejaVu Sans", fontsize=10, color="#475569", fontcolor="#0f172a", penwidth=1.4, arrowsize=0.8];',
    ]
    dot_shapes = {"box": "box", "ellipse": "ellipse", "circle": "circle", "diamond": "diamond", "cylinder": "cylinder"}
    for node in ir.nodes:
        shape = dot_shapes.get(node.shape, "box")
        attrs = [f'label="{_dot_escape(node.label)}"', f'shape="{shape}"']
        if node.role:
            attrs.append(f'comment="role:{_dot_escape(node.role)}"')
        lines.append(f'  "{_dot_escape(node.id)}" [{", ".join(attrs)}];')
    for edge in ir.edges:
        arrow = "->" if edge.directed else "--"
        attrs = []
        if edge.label:
            attrs.append(f'label="{_dot_escape(edge.label)}"')
        if edge.style != "solid":
            attrs.append(f'style="{edge.style}"')
        suffix = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f'  "{_dot_escape(edge.source)}" {arrow} "{_dot_escape(edge.target)}"{suffix};')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _run_graphviz(dot_path: Path, svg_path: Path, png_path: Path) -> None:
    try:
        svg = subprocess.run(["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)], capture_output=True, text=True)
        if svg.returncode:
            raise RenderError(svg.stderr.strip() or "Graphviz SVG rendering failed", EXIT_GRAPHVIZ, "graphviz", "render")
        png = subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], capture_output=True, text=True)
        if png.returncode:
            raise RenderError(png.stderr.strip() or "Graphviz PNG rendering failed", EXIT_GRAPHVIZ, "graphviz", "render")
    except FileNotFoundError as exc:
        raise RenderError("Graphviz dot executable was not found", EXIT_GRAPHVIZ, "graphviz", "render") from exc


def _make_manifest(temp_path: Path, ir: DiagramIR, source_bytes: bytes, family: str) -> dict[str, Any]:
    width, height = _png_dimensions(temp_path / "diagram.png")
    artifacts = []
    for name in _artifact_names(exclude_manifest=True):
        path = temp_path / name
        artifacts.append(
            {
                "path": name,
                "media_type": _media_type(name),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    aspect_ratio = width / height if height else None
    return {
        "contract": {"version": CONTRACT_VERSION, "mermaid_subset_version": "1", "ir_schema_version": ir.schema_version},
        "generator": {
            "name": "review-brief-diagrams",
            "version": "0.1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": str(uuid.uuid4()),
        },
        "input": {"source_sha256": hashlib.sha256(source_bytes).hexdigest()},
        "diagram": {
            "family": family,
            "direction": ir.direction,
            "textual_description": f"Logical architecture flowchart containing {len(ir.nodes)} nodes and {len(ir.edges)} relationships.",
            "semantic_metadata": {"node_ids": [node.id for node in ir.nodes], "edge_ids": [edge.id for edge in ir.edges]},
        },
        "configuration": {
            "style_profile": {"name": "review-brief-default", "version": "1"},
            "background": "#ffffff",
            "font_family": "DejaVu Sans",
            "dimensions": {"width": width, "height": height, "aspect_ratio": aspect_ratio},
        },
        "tools": {"graphviz": _graphviz_version(), "svg_to_png": {"name": "graphviz", "version": _graphviz_version()}},
        "artifacts": artifacts,
        "image": {"path": "diagram.png", "media_type": "image/png", "width": width, "height": height, "aspect_ratio": aspect_ratio},
        "diagnostics": [],
        "status": "succeeded",
    }


def _artifact_names(exclude_manifest: bool = False) -> tuple[str, ...]:
    names = ("source.mmd", "ir.json", "diagram.dot", "diagram.svg", "diagram.png", "manifest.json")
    return names[:-1] if exclude_manifest else names


def _media_type(name: str) -> str:
    return {"source.mmd": "text/vnd.mermaid", "ir.json": "application/json", "diagram.dot": "text/vnd.graphviz", "diagram.svg": "image/svg+xml", "diagram.png": "image/png"}[name]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RenderError("Graphviz did not produce a PNG", EXIT_GRAPHVIZ, "invalid_artifact", "validate")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _graphviz_version() -> str:
    result = subprocess.run(["dot", "-V"], capture_output=True, text=True)
    return (result.stderr or result.stdout).strip()
