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

**Logical architecture**:
A structural view of systems, components, services, interfaces, data stores, dependencies, and logical boundaries without deployment topology or runtime interaction sequencing.
_Avoid_: Deployment architecture, sequence diagram

**Relationship role**:
A controlled semantic meaning assigned to a logical-architecture edge, such as `calls`, `depends_on`, `implements`, `exposes`, `reads`, or `writes`.
_Avoid_: Edge meaning

**Style profile**:
A named, versioned collection of typography, color, contrast, line-width, layout, and related rendering parameters.
_Avoid_: Theme when referring to a rendering contract

**Qualitative review**:
Human evaluation of a rendered PNG for non-overlap, unobscured elements, visible labels, readability, aspect ratio, and color/contrast acceptability.
_Avoid_: Pixel comparison

**Best-effort rendering**:
Rendering that produces the most acceptable valid artifact possible for an oversized or difficult diagram while recording limitations or warnings.
_Avoid_: Failed rendering when a valid artifact is produced

**Refinement loop**:
An iterative cycle in which human feedback or agent-assisted changes to retained intermediates trigger re-rendering until the output is acceptable.
_Avoid_: Approval workflow

**Deployment architecture**:
A placement and isolation view of deployments, tenants, compartments, network zones, trust zones, workloads, endpoints, and network flows.
_Avoid_: Logical architecture, runtime sequence

**Deployment container**:
A deployment-family container role representing placement or isolation, such as `tenant`, `network_zone`, `trust_zone`, `cluster`, or `namespace`.
_Avoid_: Logical boundary

**Network flow**:
A directed deployment-family relationship carrying traffic or operational interaction between deployment objects, with optional protocol, port, and boundary-crossing metadata.
_Avoid_: Logical dependency

**Style profile**:
A named, versioned collection of typography, color, contrast, line-width, layout, and related rendering parameters.
_Avoid_: Theme when referring to a rendering contract

**Qualitative review**:
Human evaluation of a rendered PNG for non-overlap, unobscured elements, visible labels, readability, aspect ratio, and color/contrast acceptability.
_Avoid_: Pixel comparison
