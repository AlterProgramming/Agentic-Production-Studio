# Accessibility and Responsive Requirements

These requirements are shared and binding.

## Semantic and keyboard access

- Provide one programmatic page title and one top-level heading per route.
- Use landmarks and semantic controls appropriate to their behavior.
- Every action must be reachable and operable with a keyboard.
- Visible focus must have sufficient contrast and must not be clipped or obscured.
- Do not make a noninteractive element behave like a button or link without equivalent semantics.
- Selection state must be communicated programmatically, not only by color.
- Expanded and collapsed state must be communicated programmatically.
- When a disclosure, dialog, or detail surface closes, focus must return to a logical control.
- Skip or bypass repeated navigation where appropriate.

## Text, images, and media

- Preserve readable text resizing through at least 200 percent.
- Use the approved alternative text from image provenance, or a more context-specific equivalent that preserves the factual meaning.
- Do not place essential text only inside images.
- Source acknowledgements and external-link purpose must be understandable.
- Do not autoplay audio or video. Audio and video are not required.

## Contrast and motion

- Text and meaningful interface graphics must meet WCAG 2.2 AA contrast expectations.
- Focus indicators and selected states must remain perceivable in forced-colors or equivalent high-contrast review where feasible.
- Respect `prefers-reduced-motion: reduce`.
- Motion must not be necessary to understand route, selection, expansion, or progress state.
- Avoid flashes or rapid changes that could trigger seizures or vestibular discomfort.

## Responsive behavior

Validate at minimum:

- 1440 × 1000 desktop;
- 1024 × 768 compact desktop or tablet;
- 390 × 844 mobile;
- 320 × 700 narrow mobile.

At every required width:

- no page-level horizontal overflow;
- no clipped controls or inaccessible content;
- route navigation remains usable;
- the learning-path decision remains understandable and operable;
- expanded milestone and artifact details remain usable;
- source links and long titles wrap without collision;
- content order remains logical when linearized;
- touch targets are at least 44 × 44 CSS pixels where applicable;
- zoom and text resizing do not require two-dimensional scrolling for ordinary reading content.

## Validation honesty

Record the tools and methods actually used. Do not claim assistive-technology, browser-engine, color-contrast, or mobile-device validation that did not occur.
