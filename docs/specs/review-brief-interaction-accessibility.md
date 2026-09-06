# Review Brief interaction and accessibility

Status: accepted design specification

## Navigation model

The brief is a linear, single-page document with a persistent table of contents and hash-link navigation. The index is a sticky, collapsible sidebar on wide screens and an in-flow, collapsible block above the content on narrow screens. The initial responsive breakpoint is 768px. The index uses native `<details>/<summary>` semantics, is open by default on wide screens and closed by default on narrow screens, and preserves its open/closed state only for the current page load. It remains keyboard accessible and does not require JavaScript.

A skip-to-main link appears before repeated navigation. Top-level sections and indexed destinations have stable IDs. Ordinary fragment links update the URL and browser history; back/forward restores the fragment target. Deep links reveal containing disclosures before scrolling. JavaScript may add active-section highlighting, copy-link controls, and expand-all/collapse-all controls, but these are optional enhancements.

When a narrow-screen index link is activated, the index closes and focus moves to the destination heading. Manual dismissal returns focus to the index control. Escape closes the open narrow-screen index and returns focus to its control. Focused headings and controls remain visible below sticky UI through scroll margins or equivalent positioning.

## Progressive disclosure

Summaries, claims, risks, uncertainties, and required source links remain available in the document and are not hidden behind essential interaction. Secondary explanations, supporting evidence, and lower-priority detail may use native disclosures. Review-critical or high-priority disclosures open by default; genuinely secondary detail may be collapsed. Browser Find can search all generated content, including collapsed content. Print CSS expands meaningful content and hides only nonfunctional controls.

## Accessibility baseline

The rendered artifact targets WCAG 2.2 Level AA. It requires one page-level `<h1>`, logical heading order, semantic landmarks, semantic lists and links, keyboard-complete operation, visible focus indicators, logical focus order, target-specific accessible names, non-color-only meaning, sufficient text and non-text contrast, reduced-motion support, reflow and 200% zoom support, and accessible names, captions, and equivalent textual descriptions for meaningful diagrams. Warnings and degraded content use semantic, programmatically associated text rather than color or icons alone.

Verification includes automated HTML/accessibility and contrast checks, keyboard-only testing, screen-reader-oriented structural inspection, reduced-motion testing, `file://` testing, responsive and zoom/reflow testing, browser Find, browser back/forward, deep links, JavaScript-disabled operation, and print/PDF inspection.

## Local-file and runtime contract

The core document works from `file://` in current evergreen desktop and mobile browsers without network requests, same-origin-dependent fetches, browser storage, server APIs, or runtime external resources. CSS and JavaScript are inline. Required diagrams and images are embedded as data URLs or sanitized inline SVG. The artifact uses a system-font stack unless a font is fully embedded. Runtime behavior is limited to reviewed inline presentation logic: no dynamic code evaluation, inline event-handler attributes, executable embedded content, or runtime network loading.

With JavaScript disabled or blocked, the brief remains readable and navigable. Native links, hash navigation, native disclosures, semantic structure, and all primary content continue to work; only enhancements may be absent.

## Visual, content, and link safety

Use a stable high-contrast default theme, with optional `prefers-color-scheme` adaptation only when meaning and contrast remain equivalent. Treat generated text and source excerpts as untrusted: escape HTML by default, sanitize permitted rich markup and SVG, remove scripts and active external references, and prohibit executable generated content. Permit `https:`, `http:`, and required `file:` links; reject executable or unsafe schemes such as `javascript:` and `data:` for ordinary links. Do not load remote source resources automatically.

Generated summaries, explanations, recommendations, and diagram descriptions are visibly labeled and retain generator provenance without implying independent verification. Direct evidence, unresolved references, unavailable links, and warnings are explicitly labeled. Invalid required structure, unsafe content, contract-breaking references, inaccessible required controls, and missing essential alternatives fail generation; optional unresolved or unsupported material renders visibly with warnings.

## Print behavior

Print output preserves the same content and hierarchy, expands meaningful disclosures, prints a compact index outline with destination labels and useful source URLs, and hides navigation-only, copy-link, and other nonfunctional controls. It avoids breaks immediately after headings, keeps headings with following content, avoids splitting compact evidence cards where practical, and permits long diagrams or code to split when necessary. It does not fetch or reveal content omitted from the interactive brief.

## Read-only boundary

Controls are limited to navigation, disclosures, optional copy-link, and optional expand/collapse enhancements. The artifact contains no editable reviewer fields, approval controls, persistent reviewer state, or governance workflow. Source forms and editable examples render as non-editable review content unless explicitly required by a future specification.
