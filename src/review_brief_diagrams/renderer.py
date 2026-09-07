from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ArtifactBundle, Container, DiagramIR, Edge, Node
from .styles import DEFAULT_STYLE, StyleProfile, contrast_ratio, resolve_style

CONTRACT_VERSION = "1"
EXIT_INVALID = 2
EXIT_TRANSFORM = 3
EXIT_GRAPHVIZ = 4
EXIT_FILESYSTEM = 5
EXIT_INTERNAL = 6

FLOWCHART_RE = re.compile(r"^\s*flowchart(?:\s+(?P<direction>TB|TD|BT|RL|LR))?\s*$")
EDGE_OPERATOR_RE = re.compile(r"(-->|---|-.->|==>|-\.-)")
ROLE_RE = re.compile(r"^\[(?P<role>[a-z_]+)\]\s*(?P<label>.*)$")
ROLE_EDGE_RE = re.compile(r"^\[(?P<role>[a-z_]+)\]\s*(?P<label>.*)$")
ENDPOINT_RE = re.compile(r"^(?P<id>[A-Za-z_][\w-]*)(?P<body>.*)$")
SUBGRAPH_RE = re.compile(r"^subgraph\s+(?P<id>[A-Za-z_][\w-]*)(?:\[\"(?P<label>.*?)\"\]|\[(?P<plain_label>.*?)\])?\s*$")
END_RE = re.compile(r"^end\s*$")

LOGICAL_ROLES = {"system", "component", "service", "interface", "data_store", "external_actor", "external_system", "library", "boundary"}
DEPLOYMENT_CONTAINER_ROLES = {"deployment", "tenant", "compartment", "network_zone", "trust_zone", "availability_zone", "cluster", "namespace", "host", "boundary"}
DEPLOYMENT_NODE_ROLES = {"workload", "service", "endpoint", "gateway", "load_balancer", "database", "queue", "cache", "worker", "external_system", "external_actor", "identity", "secret_store"}
NETWORK_ROLES = DEPLOYMENT_CONTAINER_ROLES | DEPLOYMENT_NODE_ROLES
RELATIONSHIP_ROLES = {"calls", "depends_on", "implements", "exposes", "reads", "writes", "publishes", "subscribes", "contains", "references", "associates_with"}
NETWORK_RELATIONSHIP_ROLES = {"network_flow", "ingress", "egress", "routes_to", "connects_to", "replicates_to", "publishes_to", "consumes_from", "administers"}
SHAPE_BY_ROLE = {"system": "box", "component": "box", "service": "box", "interface": "ellipse", "data_store": "cylinder", "external_actor": "circle", "external_system": "box", "library": "box", "boundary": "box", "workload": "box", "endpoint": "ellipse", "gateway": "hexagon", "load_balancer": "hexagon", "database": "cylinder", "queue": "parallelogram", "cache": "cylinder", "worker": "box", "identity": "ellipse", "secret_store": "folder"}


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
        elif not quote and char in ")]}":
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
    if role not in LOGICAL_ROLES | NETWORK_ROLES:
        return label.strip(), None
    return match.group("label").strip() or role, role


def _split_edge_role(label: str | None) -> tuple[str | None, str]:
    if not label:
        return label, "relates_to"
    match = ROLE_EDGE_RE.match(label.strip())
    if not match:
        return label.strip(), "relates_to"
    role = match.group("role")
    if role not in RELATIONSHIP_ROLES | NETWORK_RELATIONSHIP_ROLES:
        return label.strip(), "relates_to"
    return match.group("label").strip() or None, role


def _parse_endpoint(token: str) -> tuple[str, str, str]:
    match = ENDPOINT_RE.match(token.strip())
    if not match:
        raise RenderError(f"invalid node endpoint: {token}", EXIT_INVALID, "invalid_syntax", "parse")
    node_id = match.group("id")
    body = match.group("body")
    if not body:
        return node_id, node_id, "box"
    pairs = (
        ("[(", ")]", "cylinder"),
        ("((", "))", "circle"),
        ("[", "]", "box"),
        ("(", ")", "ellipse"),
        ("{", "}", "diamond"),
    )
    for prefix, suffix, shape in pairs:
        if body.startswith(prefix) and body.endswith(suffix):
            label = body[len(prefix) : -len(suffix)]
            if label.startswith('"') and label.endswith('"'):
                label = label[1:-1]
            return node_id, label.strip() or node_id, shape
    raise RenderError(f"invalid node endpoint: {token}", EXIT_INVALID, "invalid_syntax", "parse")


def _shape_for(role: str | None, syntax_shape: str) -> str:
    return SHAPE_BY_ROLE[role] if role in SHAPE_BY_ROLE else syntax_shape


def _container_header(line: str) -> Container | None:
    match = SUBGRAPH_RE.match(line.strip())
    if not match:
        return None
    label = match.group("label") or match.group("plain_label") or match.group("id")
    clean_label, role = _split_role(label)
    return Container(match.group("id"), clean_label, role or "boundary")


def _parse_flow_metadata(label: str | None) -> tuple[str | None, str, dict[str, str]]:
    if not label:
        return None, "relates_to", {}
    tokens = re.findall(r"\[([^\]]+)\]", label)
    display = re.sub(r"\[[^\]]+\]", "", label).strip() or None
    role = "relates_to"
    metadata: dict[str, str] = {}
    for token in tokens:
        if token in NETWORK_RELATIONSHIP_ROLES:
            role = token
        elif ":" in token:
            key, value = token.split(":", 1)
            if key in {"HTTPS", "HTTP", "TCP", "UDP", "gRPC"}:
                metadata["protocol"] = key
                metadata["port"] = value
        elif token in {"ingress", "egress"}:
            metadata["direction"] = token
        elif token == "trust_boundary":
            metadata["trust_boundary"] = "true"
        elif token:
            metadata.setdefault("annotation", token)
    return display, role, metadata


def _validate_deployment_family(ir: DiagramIR) -> None:
    node_ids = {node.id for node in ir.nodes}
    container_ids = {container.id for container in ir.containers}
    for container in ir.containers:
        if container.role not in DEPLOYMENT_CONTAINER_ROLES:
            raise RenderError(f"unsupported deployment container role: {container.role}", EXIT_TRANSFORM, "semantic_validation", "validate")
        if container.parent_id and container.parent_id not in container_ids:
            raise RenderError(f"unresolved parent container: {container.parent_id}", EXIT_TRANSFORM, "semantic_validation", "validate")
    for node in ir.nodes:
        if node.role not in DEPLOYMENT_NODE_ROLES:
            raise RenderError(f"unsupported deployment node role: {node.role}", EXIT_TRANSFORM, "semantic_validation", "validate")
        if node.container_id and node.container_id not in container_ids:
            raise RenderError(f"unresolved container: {node.container_id}", EXIT_TRANSFORM, "semantic_validation", "validate")
    for edge in ir.edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            raise RenderError(f"unresolved network-flow endpoint: {edge.id}", EXIT_TRANSFORM, "semantic_validation", "validate")
        if edge.role not in NETWORK_RELATIONSHIP_ROLES:
            raise RenderError(f"deployment edges require network-flow metadata: {edge.id}", EXIT_TRANSFORM, "semantic_validation", "validate")


def _validate_logical_family(ir: DiagramIR) -> None:
    node_ids = {node.id for node in ir.nodes}
    container_ids = {container.id for container in ir.containers}
    for node in ir.nodes:
        if node.container_id and node.container_id not in container_ids:
            raise RenderError(f"unresolved container: {node.container_id}", EXIT_TRANSFORM, "semantic_validation", "validate")
        if node.role in NETWORK_ROLES - LOGICAL_ROLES:
            raise RenderError(f"deployment role is not valid in logical architecture: {node.role}", EXIT_TRANSFORM, "semantic_validation", "validate")
    for edge in ir.edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            raise RenderError(f"unresolved relationship endpoint: {edge.id}", EXIT_TRANSFORM, "semantic_validation", "validate")
        if edge.role in NETWORK_RELATIONSHIP_ROLES:
            raise RenderError(f"deployment relationship is not valid in logical architecture: {edge.role}", EXIT_TRANSFORM, "semantic_validation", "validate")


def parse_flowchart(source: str, family: str) -> DiagramIR:
    lines = [line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("%%")]
    if not lines or FLOWCHART_RE.match(lines[0]) is None:
        raise RenderError("expected a flowchart declaration", EXIT_INVALID, "unsupported_syntax", "parse")
    direction_match = FLOWCHART_RE.match(lines[0])
    assert direction_match is not None
    direction = direction_match.group("direction") or ("TB" if family == "deployment" else "LR")
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    containers: list[Container] = []
    stack: list[str] = []
    for line_number, line in enumerate(lines[1:], start=2):
        container = _container_header(line)
        if container:
            parent = stack[-1] if stack else None
            container = replace(container, parent_id=parent)
            if any(existing.id == container.id for existing in containers):
                raise RenderError(f"duplicate container declaration: {container.id}", EXIT_INVALID, "invalid_syntax", "parse")
            containers.append(container)
            stack.append(container.id)
            continue
        if END_RE.match(line):
            if not stack:
                raise RenderError("unmatched container end", EXIT_INVALID, "invalid_syntax", "parse")
            stack.pop()
            continue
        edge_parts = _split_edge(line)
        if edge_parts:
            source_token, operator, raw_label, target_token = edge_parts
            source_id, source_label, source_shape = _parse_endpoint(source_token)
            target_id, target_label, target_shape = _parse_endpoint(target_token)
            container_id = stack[-1] if stack else None
            source_label, source_role = _split_role(source_label)
            target_label, target_role = _split_role(target_label)
            if family == "logical":
                source_role = source_role or None
                target_role = target_role or None
            else:
                source_role = source_role or "workload"
                target_role = target_role or "workload"
            if family == "deployment":
                edge_label, edge_role, metadata = _parse_flow_metadata(raw_label)
            else:
                edge_label, edge_role = _split_edge_role(raw_label)
                metadata = {}
            nodes.setdefault(source_id, Node(source_id, source_label, _shape_for(source_role, source_shape), source_role, container_id))
            nodes.setdefault(target_id, Node(target_id, target_label, _shape_for(target_role, target_shape), target_role, container_id))
            edges.append(Edge(f"edge-{len(edges) + 1}", source_id, target_id, edge_label, edge_role, operator != "---", "dashed" if "-." in operator else "solid"))
            continue
        try:
            node_id, label, shape = _parse_endpoint(line.strip())
        except RenderError:
            raise RenderError(f"unsupported Mermaid syntax on line {line_number}", EXIT_INVALID, "unsupported_syntax", "parse")
        label, role = _split_role(label)
        role = role or ("workload" if family == "deployment" else None)
        if node_id in nodes and nodes[node_id].label not in (node_id, label):
            raise RenderError(f"duplicate node declaration: {node_id}", EXIT_INVALID, "invalid_syntax", "parse")
        nodes[node_id] = Node(node_id, label, _shape_for(role, shape), role, stack[-1] if stack else None)
    if stack:
        raise RenderError("unclosed container", EXIT_INVALID, "invalid_syntax", "parse")
    if not nodes:
        raise RenderError("flowchart contains no nodes", EXIT_TRANSFORM, "semantic_validation", "validate")
    ir = DiagramIR(family, direction, tuple(nodes.values()), tuple(edges), tuple(containers))
    if family == "logical":
        _validate_logical_family(ir)
    else:
        _validate_deployment_family(ir)
    return ir


def parse_logical_flowchart(source: str) -> DiagramIR:
    return parse_flowchart(source, "logical")


def parse_deployment_flowchart(source: str) -> DiagramIR:
    return parse_flowchart(source, "deployment")




def _validate_style(style: StyleProfile) -> None:
    if contrast_ratio(style.text_color, style.background) < 4.5:
        raise RenderError("style profile fails text contrast validation", EXIT_INVALID, "style_validation", "validate")
    if style.font_size < style.min_font_size or style.edge_font_size < style.min_font_size:
        raise RenderError("style profile uses an unreadable font size", EXIT_INVALID, "style_validation", "validate")
    if style.max_width <= 0 or style.max_height <= 0:
        raise RenderError("style profile dimensions must be positive", EXIT_INVALID, "style_validation", "validate")


def render_request(request_path: str | Path) -> ArtifactBundle:
    request_file = Path(request_path).resolve()
    try:
        request = json.loads(request_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RenderError(str(exc), EXIT_FILESYSTEM, "filesystem", "request") from exc
    source_path, bundle_path, family = _validate_request(request, request_file.parent)
    if bundle_path.exists():
        raise RenderError(f"artifact bundle already exists: {bundle_path}", EXIT_FILESYSTEM, "filesystem", "request")
    try:
        source_bytes = source_path.read_bytes()
        ir = parse_deployment_flowchart(source_bytes.decode("utf-8")) if family == "deployment" else parse_logical_flowchart(source_bytes.decode("utf-8"))
        style = resolve_style(request)
        _validate_style(style)
    except RenderError:
        raise
    except (OSError, UnicodeDecodeError) as exc:
        raise RenderError(str(exc), EXIT_FILESYSTEM, "filesystem", "source") from exc
    temp_path = Path(tempfile.mkdtemp(prefix=f".{bundle_path.name}.", dir=bundle_path.parent))
    try:
        (temp_path / "source.mmd").write_bytes(source_bytes)
        (temp_path / "ir.json").write_text(json.dumps(ir.as_dict(), indent=2) + "\n", encoding="utf-8")
        (temp_path / "diagram.dot").write_text(to_dot(ir, style), encoding="utf-8")
        _run_graphviz(temp_path / "diagram.dot", temp_path / "diagram.svg", temp_path / "diagram.png")
        (temp_path / "manifest.json").write_text(json.dumps(_make_manifest(temp_path, ir, source_bytes, family, style), indent=2) + "\n", encoding="utf-8")
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
    source_value, bundle_value, family = source.get("path"), output.get("bundle_dir"), diagram.get("family")
    if not isinstance(source_value, str) or not isinstance(bundle_value, str):
        raise RenderError("source.path and output.bundle_dir must be strings", EXIT_INVALID, "invalid_request", "request")
    if family not in {"logical", "deployment"}:
        raise RenderError("supported families are logical and deployment", EXIT_INVALID, "invalid_request", "request")
    source_path = Path(source_value) if Path(source_value).is_absolute() else base_dir / source_value
    bundle_path = Path(bundle_value) if Path(bundle_value).is_absolute() else base_dir / bundle_value
    if not source_path.is_file():
        raise RenderError(f"source file does not exist: {source_path}", EXIT_FILESYSTEM, "filesystem", "source")
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    return source_path, bundle_path, family


def to_dot(ir: DiagramIR, style: StyleProfile = DEFAULT_STYLE) -> str:
    direction = {"TB": "TB", "TD": "TB", "BT": "BT", "RL": "RL", "LR": "LR"}[ir.direction]
    lines = [
        "digraph review_brief {",
        f'  rankdir="{direction}";',
        f'  graph [bgcolor="{"transparent" if style.transparent else style.background}", pad="0.35", nodesep="0.55", ranksep="0.8", splines="polyline", outputorder="edgesfirst"];',
        f'  node [fontname="{_dot_escape(style.font_family)}", fontsize={style.font_size}, style="rounded,filled", color="{style.node_border}", fontcolor="{style.text_color}", fillcolor="{style.node_fill}", margin="{style.node_margin}"];',
        f'  edge [fontname="{_dot_escape(style.font_family)}", fontsize={style.edge_font_size}, color="{style.edge_color}", fontcolor="{style.text_color}", penwidth={style.line_width}, arrowsize={style.arrow_size}];',
    ]
    for container in ir.containers:
        lines.append(f'  subgraph "cluster_{_dot_escape(container.id)}" {{ label="{_dot_escape(container.label)}"; comment="role:{_dot_escape(container.role)}"; }}')
    for node in ir.nodes:
        attrs = [f'label="{_dot_escape(node.label)}"', f'shape="{node.shape}"']
        if node.role:
            attrs.append(f'comment="role:{_dot_escape(node.role)}"')
        lines.append(f'  "{_dot_escape(node.id)}" [{", ".join(attrs)}];')
    for edge in ir.edges:
        attrs = []
        if edge.label:
            attrs.append(f'label="{_dot_escape(edge.label)}"')
        if edge.role != "relates_to":
            attrs.append(f'comment="role:{_dot_escape(edge.role)}"')
        if edge.style != "solid":
            attrs.append(f'style="{edge.style}"')
        suffix = f" [{', '.join(attrs)}]" if attrs else ""
        arrow = "->" if edge.directed else "--"
        lines.append(f'  "{_dot_escape(edge.source)}" {arrow} "{_dot_escape(edge.target)}"{suffix};')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _run_graphviz(dot_path: Path, svg_path: Path, png_path: Path) -> None:
    try:
        for output, path in (("svg", svg_path), ("png", png_path)):
            result = subprocess.run(["dot", f"-T{output}", str(dot_path), "-o", str(path)], capture_output=True, text=True)
            if result.returncode:
                raise RenderError(result.stderr.strip() or f"Graphviz {output} rendering failed", EXIT_GRAPHVIZ, "graphviz", "render")
    except FileNotFoundError as exc:
        raise RenderError("Graphviz dot executable was not found", EXIT_GRAPHVIZ, "graphviz", "render") from exc


def _make_manifest(temp_path: Path, ir: DiagramIR, source_bytes: bytes, family: str, style: StyleProfile = DEFAULT_STYLE) -> dict[str, Any]:
    width, height = _png_dimensions(temp_path / "diagram.png")
    artifacts = []
    for name in _artifact_names(exclude_manifest=True):
        path = temp_path / name
        artifacts.append({"path": name, "media_type": _media_type(name), "bytes": path.stat().st_size, "sha256": _sha256(path)})
    aspect_ratio = width / height if height else None
    return {
        "contract": {"version": CONTRACT_VERSION, "mermaid_subset_version": "1", "ir_schema_version": ir.schema_version},
        "generator": {"name": "review-brief-diagrams", "version": "0.1.0", "generated_at": datetime.now(timezone.utc).isoformat(), "run_id": str(uuid.uuid4())},
        "input": {"source_sha256": hashlib.sha256(source_bytes).hexdigest()},
        "diagram": {"family": family, "direction": ir.direction, "textual_description": f"{family.title()} architecture flowchart containing {len(ir.nodes)} nodes, {len(ir.edges)} relationships, and {len(ir.containers)} containers.", "semantic_metadata": {"node_ids": [node.id for node in ir.nodes], "edge_ids": [edge.id for edge in ir.edges], "container_ids": [container.id for container in ir.containers], "edge_roles": {edge.id: edge.role for edge in ir.edges}}},
        "configuration": {"style_profile": style.as_dict(), "dimensions": {"width": width, "height": height, "aspect_ratio": aspect_ratio}},
        "tools": {"graphviz": _graphviz_version(), "svg_to_png": {"name": "graphviz", "version": _graphviz_version()}},
        "artifacts": artifacts,
        "image": {"path": "diagram.png", "media_type": "image/png", "width": width, "height": height, "aspect_ratio": aspect_ratio},
        "diagnostics": [], "status": "succeeded",
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
