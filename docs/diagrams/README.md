# Diagram generator

The `review-brief-diagrams` package renders constrained Mermaid inputs into inspectable artifact bundles for Review Brief.

## Support matrix

| Family | Source form | Default direction | Status |
| --- | --- | --- | --- |
| logical | `flowchart` | `LR` | supported |
| deployment | `flowchart` | `TB` | supported |
| interaction | `sequenceDiagram` | participant lanes | supported |

The renderer does not inspect repositories, pull/merge requests, or documentation. Mermaid distillation is an upstream responsibility.

## Installation

Requirements:

- Python 3.11 or newer.
- Graphviz `dot` available on `PATH`.

Install in an isolated environment:

```bash
python -m pip install -e .
```

## Invocation

Create a JSON request. Relative paths resolve from the request file's directory:

```json
{
  "contract_version": "1",
  "source": {"path": "architecture.mmd"},
  "diagram": {"family": "logical"},
  "output": {"bundle_dir": "artifacts/architecture"},
  "rendering": {
    "style_profile": "review-brief-default"
  }
}
```

Run the CLI:

```bash
diagram-render request.json
```

The request requires `source.path`, `diagram.family`, and `output.bundle_dir`. `contract_version` is optional and defaults to the latest supported version. Use an inline `rendering.style_profile` object for constrained style overrides. Existing artifact bundles are not overwritten.

## Artifact bundle

A successful invocation produces:

- `source.mmd` — retained Mermaid bytes.
- `ir.json` — semantic intermediate representation.
- `diagram.dot` — Graphviz input.
- `diagram.svg` — inspectable vector intermediate.
- `diagram.png` — final raster representation.
- `manifest.json` — authoritative metadata and handoff document.

The manifest records contract and IR versions, generator run metadata, source hash, family, textual description, semantic IDs and roles, resolved style profile, tool versions, artifact hashes, image dimensions/aspect ratio, diagnostics, and status.

## Status and diagnostics

Stable exit-code classes:

- `0` — success.
- `2` — invalid request, unsupported syntax, or invalid style profile.
- `3` — semantic transformation or family validation failure.
- `4` — Graphviz rendering failure.
- `5` — filesystem or artifact-write failure.
- `6` — internal generator failure.

Failures are emitted as structured JSON diagnostics on stderr. The artifact bundle is published only after successful rendering and validation.

## Handoff boundary

The downstream Review Brief consumer should use `manifest.json` as the authoritative handoff. It resolves artifact paths relative to the manifest, validates supported contract versions, confines artifacts to the bundle, rejects unsafe SVG content, and maps the PNG, textual description, semantic metadata, warnings, and reproducibility information into the Review Brief diagram representation.

The renderer does not own Review Brief HTML layout, navigation, claims, explanations, risks, uncertainties, approval handling, or repository-to-Mermaid distillation.

## Verification

From the repository root:

```bash
PYTHONPATH=src pytest -q
python -m compileall -q src tests
python -m pip install -e .
diagram-render --help
```

Pixel comparison is not required. Tests verify conversion-path success, artifact presence, manifest contents, diagnostics, semantic validation, style validation, and handoff safety. Human qualitative review remains the acceptance mechanism for visual refinement.
