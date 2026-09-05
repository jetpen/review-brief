# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`docs/adr/`** for decisions that touch the area being changed.

If any of these files do not exist, proceed silently. Do not flag their absence or suggest creating them upfront. Create them lazily when domain terms or architectural decisions actually require them.

## File structure

This is a single-context repository:

```text
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-example-decision.md
│   └── 0002-example-decision.md
└── src/
```

## Use the glossary's vocabulary

When output names a domain concept, use the term defined in `CONTEXT.md`. Do not drift to synonyms that the glossary explicitly avoids.

If the needed concept is not in the glossary, treat that as a possible domain-modeling gap rather than silently inventing terminology.

## Flag ADR conflicts

If proposed work contradicts an existing ADR, surface the conflict explicitly rather than silently overriding it:

> _Contradicts ADR-0007 — but worth revisiting because…_
