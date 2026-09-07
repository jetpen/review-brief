# Review Brief

Review Brief is an agent skill for turning machine-generated outputs into concise, human-reviewable presentations.

It produces a self-contained HTML/CSS/JavaScript single-page application with no backend. The application organizes the most important evidence, explanations, diagrams, and approval decisions so a human can understand what the machine produced and decide whether to accept it.

## Goals

- Reduce the effort required to review machine outputs.
- Put the highest-priority review items at the top level.
- Link directly to source material when no explanation is needed.
- Explain complex material with concise summaries and visual diagrams.
- Make assumptions, uncertainties, risks, and requested decisions explicit.
- Produce an artifact that can be opened locally without a server.

## Core output

Each review brief is a single-page application containing:

1. **Review index** — hyperlinks to the most important things to inspect.
2. **Source links** — direct links to files, diffs, logs, reports, or other evidence when the destination is self-explanatory.
3. **Explanations and summaries** — concise context for evidence that requires interpretation.
4. **Diagrams** — visual representations of complex relationships, processes, architectures, or decision paths.
5. **Review decisions** — explicit approval, rejection, follow-up, or clarification points.

The index should distinguish between:

- Items requiring a decision.
- Items requiring verification.
- Background information.
- Direct evidence.

## Design principles

- **Human-first:** optimize for fast comprehension, not machine completeness.
- **Evidence-linked:** every material claim should point to its source.
- **Progressive detail:** show the decision-relevant summary first, with deeper evidence one link away.
- **Explicit uncertainty:** identify missing evidence, assumptions, confidence, and unresolved risks.
- **Visual compression:** use diagrams where structure is easier to understand visually than as prose.
- **No backend:** the generated brief must work as a local file without network services or application infrastructure.
- **Reviewable output:** the presentation should make clear what the human is being asked to approve.

## Intended workflow

1. An agent gathers machine outputs and their source material.
2. The agent identifies the highest-value review points.
3. The agent writes explanations and creates diagrams where needed.
4. The agent generates a self-contained HTML/CSS/JavaScript brief.
5. A human opens the brief, follows the index, reviews the evidence, and records or communicates an approval decision.

## Initial scope

The first implementation will define:

- The review-brief content model.
- A reusable single-page HTML layout.
- CSS for clear hierarchy and readable evidence sections.
- JavaScript for navigation and lightweight interaction.
- Conventions for source links, diagrams, risks, and approval requests.
- Agent instructions for producing consistent review briefs.

## Non-goals

- Hosting or serving review briefs.
- Storing review data in a database.
- Replacing the underlying source material.
- Hiding uncertainty or presenting machine output as independently verified fact.

## Design specifications

- [Review Brief content model](docs/specs/review-brief-content-model.md)
- [Review Brief JSON Schema](docs/specs/review-brief.schema.json)
- [Review Brief information architecture](docs/specs/review-brief-information-architecture.md)
- [Review Brief interaction and accessibility](docs/specs/review-brief-interaction-accessibility.md)

## Minimal diagram renderer

The first implementation tracer bullet is available as the `diagram-render` CLI. It accepts a JSON render request and supports logical-architecture and deployment `flowchart` input plus constrained `sequenceDiagram` interaction input through Graphviz `dot`, including semantic roles, relationship roles, nested boundaries, and ordered messages.

Requirements:

- Python 3.11 or newer
- Graphviz `dot` available on `PATH`

Install the package in an isolated environment:

```bash
python -m pip install -e .
```

Create a request containing `source.path`, `diagram.family: "logical"`, and `output.bundle_dir`, then run:

```bash
diagram-render --request request.json
```

For interactive use, equivalent request properties can be supplied directly:

```bash
diagram-render --source architecture.mmd --family logical --output artifacts/architecture
```

The `--request` qualifier is mandatory for JSON mode; positional request paths are rejected. `--contract-version` is optional and defaults to the latest supported version.

A successful artifact bundle contains `source.mmd`, `ir.json`, `diagram.dot`, `diagram.svg`, `diagram.png`, and `manifest.json`. Relative paths in the request resolve from the request file's directory. Existing bundles are not overwritten. Invalid requests, unsupported Mermaid syntax, and invalid style profiles return structured JSON diagnostics on stderr and stable nonzero exit codes.

A request may select a named versioned style profile through `rendering.style_profile`. The default profile is `review-brief-default` version `1`; an inline profile object can override typography, colors, contrast, line widths, dimensions, label wrapping, and transparency. The resolved profile is recorded in the manifest and validated for readable contrast and font sizes. Corporate branding or style-guide tooling can synthesize profile objects without changing the renderer contract.

## Repository status

The repository contains the Mermaid-to-PNG generator implementation with logical, deployment, and interaction diagram support. Manifest-authoritative handoff validation and packaging improvements are tracked in GitHub issues.

A downstream consumer can validate a generated bundle with `review_brief_diagrams.handoff.validate_handoff("path/to/manifest.json")`. The validator confines artifact paths to the bundle, checks supported contract versions, exposes PNG and semantic metadata for Review Brief, and rejects unsafe SVG content.
