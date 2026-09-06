# Review Brief content model

Status: accepted design specification

## Purpose and boundary

A Review Brief is a self-contained, backend-free HTML artifact that helps a person understand a Git repository or a bounded pull/merge request. It links to or selectively summarizes the reviewed material; it does not replace the repository, archive its contents, solicit approval, record approval, or provide governance, audit, compliance, or decision-record features.

The brief has one understanding objective. It may cover repository-wide context and a pull/merge-request scope together when the target makes the primary scope and broader contextual scope visible.

## Canonical top-level model

The canonical serialized representation is JSON-compatible JSON. The required top-level fields are:

- `metadata`
- `target`
- `objective`
- `index`

Optional collections are omitted when unused:

- `sources`
- `summaries`
- `explanations`
- `claims`
- `diagrams`
- `risks`
- `uncertainties`

The model uses flat typed collections with local IDs and explicit references. IDs are required for objects that are indexed or cross-referenced; they need only be unique within one brief.

## Metadata

`metadata` contains:

- `brief_id`
- `title`
- `schema_version`
- `generator`: `name`, `version`, `invocation_id`, and `generated_at`

Generator provenance explains artifact origin. It is not an audit record. Prompt, model, environment, tool transcript, and execution-log capture are not required.

## Target

`target` identifies the reviewed subject without embedding the repository.

A repository target contains:

- `kind: "repository"`
- `repository_locator`: a remote Git URL or local filesystem path
- optional `branch`
- optional `revision`

A pull/merge-request target contains:

- `kind: "pull_merge_request"`
- `repository_locator`: a remote Git URL
- optional `request_id`
- `base_revision`
- `head_revision`
- optional `changed_scope` containing changed paths, diff statistics, selected hunks, or exclusions

Local repository reproducibility metadata is optional. Pull/merge-request revisions define the reviewed change range; the request ID is optional.

## Objective and index

`objective` is the question or understanding goal, not an approval decision. Examples include `understand the authentication flow` and `identify architectural coupling in this pull request`.

Each `index` entry is a prioritized pointer with:

- `id`
- `target`: an object ID or source link
- `category`: one of `finding`, `verification`, `risk`, `uncertainty`, `background`, or `direct_evidence`
- `priority`: one of `critical`, `high`, `medium`, or `low`, representing attention priority based on importance, impact, and risk relevant to human review
- `label`
- `significance`: a one-sentence explanation of why the item matters
- `scope`: one of `change`, `repository`, or `shared`
- optional `review_instruction`

Index priority controls reading order. It is not severity, truth, approval urgency, or governance state. The renderer uses the fixed descending order `critical`, `high`, `medium`, `low` and deterministic category and identifier tie-breakers defined by the information-architecture specification.

## Sources and links

A source is a structured hyperlink object:

- `id`
- `link`: any syntactically valid browser-supported URL scheme
- optional `label`
- optional `description`
- optional `locator`

Local sources may use `file:` URLs. A source link need not be reachable when the brief is generated. An unavailable link remains a valid reference and should be shown as unavailable by the renderer.

Repository files, commits, diff hunks, command-output regions, web standards, library repositories, algorithms, research, and other contextual material are all sources. The link is primary; excerpts are optional context and never replace the source link.

## Summaries and explanations

A `summary` is a compact representation of reviewed source or brief content. It has an ID, text, and references to the content it summarizes. It may also reference claims, explanations, or diagrams included in the summary.

An `explanation` adds context beyond compression. It may provide definitions, standards, design patterns, dependency context, algorithms, research, product/project context, architecture, related components, interfaces, boundaries, seams, and integrations. It has an ID, text, and optional typed references to relevant objects and external sources.

Useful explanation relationship types include `explains`, `contextualizes`, `defines`, `supports`, `contrasts_with`, and `depends_on`.

## Claims, recommendations, risks, and uncertainties

Claims are optional. They are used when the brief adds material interpretation beyond direct source navigation.

A claim has:

- `id`
- `text`
- `kind`: a non-empty generator-declared vocabulary value
- optional typed references to sources, supporting claims, explanations, risks, or uncertainties
- optional `confidence` containing a declared scale and assessed value

A recommendation is a claim whose kind is `recommendation`. Recommendations are analytical content, not approval requests.

A material claim must reference direct sources, supporting claims, or both. An assumption may lack direct source support only when it is explicitly marked with an assumption kind. Claims do not require a status or truth-value field.

Risks and uncertainties are separate annotation objects. Each has an ID, description, affected claims or scope, and optional source or basis references. They remain explanatory annotations; they do not contain owners, deadlines, mitigations, approval state, or workflow fields.

## Diagrams

A diagram is a presentational artifact with:

- `id`
- `type`
- `title`
- `representation`, commonly a PNG or another rendered image
- references to represented claims, sources, or other objects
- optional rendering metadata

The content model does not mandate a rendering tool. Mermaid, Graphviz, image-generation tools, infographic tools, and other renderers are permitted. Rendering metadata may identify the inputs or tools, but semantic references to represented objects are more important than the rendering pipeline.

Material visual assertions must reference the relevant source, claim, or evidence. If a referenced object is unavailable, the diagram remains valid while exposing the unresolved reference.

## Reference and validation rules

- Collections are flat and references are explicit.
- A claim may reference many sources; a source may support many claims.
- Summaries and explanations reference the material they present or contextualize.
- Index targets must identify an addressable object or source link.
- Known cross-references must resolve to IDs or valid source links.
- Source links must be syntactically valid browser-supported URLs when present.
- Validation checks required fields, known reference integrity, object shapes, and link syntax.
- Validation does not require source availability, truth verification, or repository reproducibility.
- Unknown optional fields are ignored. Unknown object kinds render generically when possible.
- Optional collections may be omitted or rendered empty.

## Rendering boundary

The renderer produces a self-contained local HTML/CSS/JavaScript artifact. Its human-facing hierarchy, progressive-detail rules, priority ordering, scope badges, stable anchors, empty states, and unresolved-reference behavior are defined in the [information-architecture specification](review-brief-information-architecture.md).

The renderer should preserve source links, show unavailable links honestly, render known object types, and provide generic presentation for unknown optional object kinds without silently reinterpreting their semantics.
