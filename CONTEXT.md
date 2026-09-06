# Review Brief Diagram Generator Context

This context defines the shared vocabulary for the bottom-up Mermaid-to-PNG diagram generator and its handoff to the Review Brief system.

## Language

**Render request**:
A JSON document that identifies Mermaid source, diagram family, output bundle, and optional rendering or provenance metadata.
_Avoid_: Job, task payload

**Diagram family**:
An explicit semantic category that determines which Mermaid subset and transformation rules apply: logical architecture, deployment architecture, or use-case interaction.
_Avoid_: Diagram type when referring to semantic intent

**Artifact bundle**:
The isolated output directory containing the retained Mermaid source, semantic IR, Graphviz DOT, SVG, PNG, and manifest for one render invocation.
_Avoid_: Build output, result folder

**Semantic intermediate representation (IR)**:
The constrained, family-aware representation between Mermaid syntax and Graphviz DOT that preserves diagram meaning and stable identifiers.
_Avoid_: Abstract syntax tree when referring to the cross-family semantic model

**Manifest**:
The machine-readable record of the contract, generator, input, diagram, optional provenance, configuration, tools, artifacts, image metadata, diagnostics, and status for an invocation.
_Avoid_: Audit record

**Provenance**:
Optional metadata describing where Mermaid source came from, such as a repository, pull/merge request, document, revision, or source locator.
_Avoid_: Required identity

**Diagnostic bundle**:
A separately located failure output containing a manifest and any validated intermediates when generation cannot produce a successful artifact bundle.
_Avoid_: Successful bundle

**Mermaid subset**:
The versioned, explicitly supported portion of Mermaid syntax accepted for the three diagram families; unsupported syntax fails rather than being silently approximated.
_Avoid_: Mermaid compatibility

**Container**:
A first-class nested boundary in the IR that groups diagram objects and preserves stable identity, membership, family role, and boundary metadata.
_Avoid_: Group when referring to a semantic boundary

**Semantic role**:
A family-specific meaning assigned during validation and normalization rather than inferred solely from Mermaid syntax or visual shape.
_Avoid_: Shape meaning
