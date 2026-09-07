from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_CONTRACT_VERSIONS = {"1"}
ALLOWED_STATUSES = {"succeeded", "succeeded_with_warnings", "failed", "failed_with_artifacts"}
SAFE_MEDIA_TYPES = {"image/png", "image/svg+xml", "application/json", "text/vnd.mermaid", "text/vnd.graphviz"}


@dataclass(frozen=True)
class HandoffDiagnostic:
    severity: str
    category: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "category": self.category, "message": self.message}


@dataclass(frozen=True)
class HandoffResult:
    manifest_path: Path
    status: str
    compatible: bool
    diagnostics: tuple[HandoffDiagnostic, ...]
    png_path: Path | None
    metadata: dict[str, Any]

    @property
    def warnings(self) -> tuple[HandoffDiagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.severity == "warning")


def validate_handoff(manifest_path: str | Path, *, confine_to_bundle: bool = True) -> HandoffResult:
    path = Path(manifest_path).resolve()
    diagnostics: list[HandoffDiagnostic] = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return HandoffResult(path, "failed", False, (HandoffDiagnostic("error", "manifest", str(exc)),), None, {})
    if not isinstance(manifest, dict):
        return HandoffResult(path, "failed", False, (HandoffDiagnostic("error", "manifest", "manifest must be an object"),), None, {})
    contract = manifest.get("contract")
    version = contract.get("version") if isinstance(contract, dict) else None
    compatible = version in SUPPORTED_CONTRACT_VERSIONS
    if not compatible:
        diagnostics.append(HandoffDiagnostic("warning", "compatibility", f"unsupported handoff contract version: {version!r}"))
    required_sections = {"contract", "generator", "input", "diagram", "configuration", "tools", "artifacts", "image", "diagnostics", "status"}
    missing = sorted(required_sections - manifest.keys())
    if missing:
        diagnostics.append(HandoffDiagnostic("error", "manifest", f"missing manifest sections: {', '.join(missing)}"))
    status = manifest.get("status")
    if status not in ALLOWED_STATUSES:
        diagnostics.append(HandoffDiagnostic("error", "status", f"unsupported status: {status!r}"))
        status = "failed"
    bundle_root = path.parent
    artifacts = manifest.get("artifacts", [])
    artifact_paths: dict[str, Path] = {}
    if not isinstance(artifacts, list):
        diagnostics.append(HandoffDiagnostic("error", "artifacts", "artifacts must be an array"))
        artifacts = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
            diagnostics.append(HandoffDiagnostic("error", "artifacts", "artifact entries require a relative path"))
            continue
        relative = Path(artifact["path"])
        resolved = (bundle_root / relative).resolve()
        if confine_to_bundle and bundle_root not in resolved.parents:
            diagnostics.append(HandoffDiagnostic("error", "path_safety", f"artifact escapes bundle: {relative}"))
            continue
        media_type = artifact.get("media_type")
        if media_type not in SAFE_MEDIA_TYPES:
            diagnostics.append(HandoffDiagnostic("error", "media_type", f"unsafe or unsupported media type: {media_type!r}"))
        if not resolved.is_file():
            diagnostics.append(HandoffDiagnostic("error", "artifact", f"artifact is missing: {relative}"))
            continue
        artifact_paths[relative.as_posix()] = resolved
        if media_type == "image/svg+xml":
            text = resolved.read_text(encoding="utf-8", errors="replace").lower()
            if "<script" in text or "javascript:" in text or "xlink:href=\"http" in text:
                diagnostics.append(HandoffDiagnostic("error", "unsafe_svg", f"active or remote SVG content: {relative}"))
    image = manifest.get("image")
    png_path = None
    if isinstance(image, dict) and isinstance(image.get("path"), str):
        png_path = artifact_paths.get(Path(image["path"]).as_posix())
        if png_path is None:
            diagnostics.append(HandoffDiagnostic("error", "image", "manifest image path is not a validated artifact"))
    if status in {"succeeded", "succeeded_with_warnings"} and png_path is None:
        diagnostics.append(HandoffDiagnostic("error", "image", "successful handoff requires a PNG artifact"))
    if status == "succeeded_with_warnings":
        diagnostics.append(HandoffDiagnostic("warning", "status", "diagram was generated with warnings"))
    errors = tuple(d for d in diagnostics if d.severity == "error")
    if errors:
        status = "failed" if status == "succeeded" else status
    if status == "failed_with_artifacts":
        png_path = None
    return HandoffResult(path, status, compatible and not errors, tuple(diagnostics), png_path, _public_metadata(manifest))


def _public_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    diagram = manifest.get("diagram", {})
    return {
        "id": manifest.get("input", {}).get("source_sha256"),
        "type": diagram.get("family"),
        "title": diagram.get("title"),
        "description": diagram.get("textual_description"),
        "semantic_metadata": diagram.get("semantic_metadata", {}),
        "provenance": manifest.get("provenance"),
        "warnings": manifest.get("diagnostics", []),
        "rendering": {"contract": manifest.get("contract"), "generator": manifest.get("generator"), "tools": manifest.get("tools")},
    }
