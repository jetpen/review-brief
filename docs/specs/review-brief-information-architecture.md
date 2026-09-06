# Review Brief information architecture

Status: accepted design specification

## Purpose and boundary

The information architecture defines how a Review Brief presents its canonical content model as a single-page, backend-free HTML artifact. It optimizes for rapid human understanding of the most important material while preserving direct access to evidence and supporting context.

The information architecture does not solicit approval, record approval outcomes, provide governance or audit workflows, or replace the reviewed repository or pull/merge request.

## Page hierarchy

The page uses this stable hierarchy, in reading order:

1. `What matters`
2. `Evidence`
3. `Context`
4. `Risks and uncertainties`
5. `Appendix`

The serialized collection order does not determine human reading order. Empty sections and their navigation entries are omitted unless the brief explicitly declares that a section is expected.

## What matters

`What matters` is the landing section. It contains:

1. a target summary;
2. the understanding objective;
3. the `Review first` tier;
4. a compact risk/uncertainty strip;
5. the `Explore` tier.

The landing section exposes the attention frontier without duplicating the full brief.

### Target summary

The target summary identifies:

- the primary scope;
- the repository or pull/merge-request identity;
- applicable branch, request, and revision information;
- the understanding objective.

Each index item also displays its local scope because repository-wide context and change-specific material may be mixed in one unified index.

### Review first

`Review first` contains index entries in these categories:

- `finding`;
- `verification`;
- `risk`;
- `uncertainty`.

Each item displays:

- label;
- category;
- ordinal attention priority;
- one-sentence significance;
- scope badge;
- destination link.

Risks and uncertainties whose priority places them in `Review first` are surfaced in the landing section. Their complete annotations remain in `Risks and uncertainties`.

### Explore

`Explore` is a compact link list below `Review first`. It contains:

- `background` entries;
- `direct_evidence` entries.

It remains visible in the index and is not hidden in the Appendix.

## Priority and ordering

Priority is an attention priority based on importance, impact, and risk relevant to human reading. It is not severity, truth, approval urgency, or governance state.

The canonical ordinal vocabulary is:

1. `critical`;
2. `high`;
3. `medium`;
4. `low`.

The renderer displays the declared label and sorts deterministically.

For equal-priority `Review first` entries, the category order is:

1. findings;
2. verification;
3. risks;
4. uncertainties;
5. stable source or object identifier.

For equal-priority `Explore` entries, the category order is:

1. background;
2. direct evidence;
3. stable source or object identifier.

Generator order is not an implicit tie-breaker. The renderer does not infer ordering from arbitrary numeric or string values.

## Scope

Every index entry has a required scope badge with one of these values:

- `change` — material specific to the pull/merge-request change scope;
- `repository` — repository-wide material;
- `shared` — material relevant to both scopes.

Destinations inherit the index entry's scope for presentation. Supporting objects do not require a single scope because references may cross scopes.

## Progressive detail

Each indexed item has one canonical destination. A destination contains, in order:

1. destination heading;
2. one-sentence significance summary;
3. concise explanation when interpretation or context is needed;
4. associated diagram when useful;
5. evidence and source links;
6. associated risks and uncertainties.

An indexed item without a generated explanation remains valid. The renderer shows its significance summary and direct evidence links, then omits the explanation block. The renderer does not invent interpretation from a source link.

A generated summary is labeled `Generated summary`. Additional interpretation is labeled `Explanation`. Source material is labeled `Direct evidence`. These distinctions are semantic and textual, not dependent on visual styling alone.

## Destination ownership and references

An object referenced by multiple index entries has one canonical destination. Each index entry links to that destination and may use a fragment identifying the relevant aspect. Objects are not duplicated per index entry.

Index targets resolve as follows:

- object IDs resolve to generated local anchors;
- source-link targets remain direct links;
- unresolved targets remain visible and are marked as unresolved.

An unresolved reference explains what could not be resolved and links to the Appendix details. The renderer does not silently repair or replace it with an approximate match.

## Evidence

`Evidence` contains direct evidence cards and source links, including evidence linked from findings and verification items. A direct evidence card includes, when available:

- source label;
- locator;
- scope;
- direct link.

The source link remains primary. Generated interpretation is not duplicated in the Evidence section. Contextual and secondary sources belong in `Context` or the `Appendix` as appropriate.

Unavailable source links remain visible and are shown honestly as unavailable.

## Context

`Context` contains background items, explanations, definitions, architecture context, and diagrams not already inline at a canonical destination. Content is not duplicated by default.

## Risks and uncertainties

The dedicated `Risks and uncertainties` section contains complete risk and uncertainty annotations, including their references and affected scope. Material entries are also surfaced in `What matters` according to their index priority.

Risks and uncertainties remain explanatory annotations. They do not become approval state, ownership, deadlines, mitigation workflow, or governance records.

## Diagrams

A diagram appears inline in the destination item it explains, immediately after the summary or explanation. It receives its own index entry only when inspecting the diagram is itself review-critical. It is not duplicated in a dedicated section by default.

Diagrams in `Context` are diagrams that are not already attached to a canonical destination. Material visual assertions retain semantic references to relevant sources, claims, or evidence.

## Appendix

The `Appendix` contains supporting metadata, secondary sources, rendering details, unresolved-reference details, and other material not needed for first-pass understanding.

The Appendix must not hide material findings, risks, uncertainties, or required verification items.

## Navigation anchors

The canonical navigation consists of:

- stable anchors for top-level sections;
- one stable anchor per indexed destination;
- secondary anchors for supporting objects.

The serialization model does not require one user-facing anchor per object.

## Empty states

A valid brief may have an empty index. The renderer shows the objective and an explicit `no indexed review items` state rather than fabricating an entry.

Empty top-level sections and navigation entries are omitted unless the brief declares that a section is expected. An expected but empty section receives an explicit empty-state notice.

## Rendering boundary

The generation contract defines the canonical priority vocabulary and ordering. The renderer follows that declaration and does not reinterpret unknown values through heuristics.

Unknown optional object kinds render generically where possible without silently changing their semantics. Source links remain primary, unavailable links are exposed honestly, and unresolved references remain visible.
