# Architecture diagram scope

Status: accepted design specification

## Purpose

An architecture explanation in a Review Brief must show enough of the system for a reader to understand who uses it, how its major parts fit together, and how important work moves through those parts. A single diagram is not assumed to provide all three kinds of understanding.

The architecture-diagram set therefore covers three complementary views:

1. **Public interfaces and surfaces** — the interfaces through which an end user, client, operator, or external system interacts with the application.
2. **Logical architecture** — the coarse-grained subsystems, their responsibilities, dependencies, and seams.
3. **Request flows** — the ordered path through those subsystems for the most important use cases, including the response or outcome.

These views are a coverage requirement, not a requirement to produce three images. A view may be omitted only when it is genuinely inapplicable, and that omission must be stated in the brief.

## View requirements

### Public interfaces and surfaces

This view identifies the externally visible entry points and the people or systems that use them. It may include, as applicable:

- web, mobile, desktop, or command-line user interfaces;
- HTTP, RPC, GraphQL, event, webhook, or batch interfaces;
- authentication and authorization entry points;
- operator, administration, or configuration surfaces;
- externally visible outputs such as files, notifications, reports, or events.

The view should show the interface name, its consumer, and the high-level capability it exposes. Internal calls and implementation details do not belong here unless they are necessary to explain where a public surface ends.

### Logical architecture

This view shows the application as coarse-grained subsystems. Each subsystem should have a clear responsibility and a stable interface at its seam. The view should show:

- the application’s major subsystems and their responsibilities;
- the seams and interfaces between subsystems;
- important adapters or integrations at those seams;
- durable data stores or external systems when they affect ownership or flow;
- dependency direction and relationships that matter to the explanation.

The view is logical, not deployment topology. Hosts, regions, containers, network zones, and replicas belong in a deployment view only when deployment is itself relevant to the review objective.

### Request flows

This view explains how a request or event is processed through the logical subsystems and becomes a response or other outcome. Each flow should identify:

- the initiating actor or public interface;
- the ordered subsystem interactions;
- meaningful validation, authorization, transformation, persistence, integration, or publication steps;
- the response, emitted event, or failure outcome;
- important alternate or error paths when they materially change understanding.

Request flows use the interaction architecture family. They should not repeat every internal call: include the steps needed to explain the use case and the seams crossed.

## Use-case selection

By default, include at most the top five request flows. Select them using this order of importance:

1. flows central to the review objective;
2. flows exercising changed or newly introduced interfaces or seams;
3. flows representing the highest-risk or highest-impact behavior;
4. flows that explain materially different paths through the system;
5. flows needed to cover a public surface or important failure mode not otherwise represented.

If fewer than five flows are material, include fewer. Include more than five only when the request explicitly demands it or when omitting a flow would leave a material public surface, seam, or behavior unexplained. Record the reason for any expansion beyond five.

## Coverage and traceability

The diagram set should make these relationships reviewable:

```text
public interface or surface
            │ initiates
            ▼
       request flow ───── crosses ─────► logical subsystem seams
            │                                  │
            └──────── produces outcome ◄───────┘
```

Names for public surfaces, subsystems, seams, and flow participants should remain stable across views. A flow participant should map to a subsystem or public interface in the logical or public-surface view; unresolved mappings must be called out as an uncertainty rather than silently renamed.

Each material diagram must retain references to the reviewed source, claims, or evidence that support its visual assertions. The views may be rendered inline with the explanation they support or placed in `Context` when they do not have a single canonical destination.

## Diagram family mapping

| Architecture view | Diagram family | Primary question |
| --- | --- | --- |
| Public interfaces and surfaces | logical | Who interacts with the application, and through what? |
| Coarse-grained subsystems and seams | logical | What are the major parts, responsibilities, and interfaces? |
| Request flows for selected use cases | interaction | How does important work move through the parts and produce an outcome? |
| Deployment topology, when relevant | deployment | Where are the parts placed and isolated? |

Deployment architecture is supplementary. It does not replace the required public-surface, logical, or request-flow views.

## Completeness check

Before considering an architecture explanation complete, verify that:

- every material public interface or surface has a visible owner or destination;
- every coarse-grained subsystem has a responsibility and relevant seam;
- each selected request flow starts at a public interface or actor and ends at a response or outcome;
- the selected flows cover the most important use cases and do not exceed five without an explicit reason;
- names and references line up across all views;
- omissions, unresolved mappings, assumptions, and unsupported detail are visible to the reviewer.
