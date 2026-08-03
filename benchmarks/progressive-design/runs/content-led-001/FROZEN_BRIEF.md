# Frozen Product Brief — Central California Migrant Camp Voices, 1940–1941

## Product purpose
Create a public-facing digital experience that helps visitors discover, compare, and listen to a bounded set of oral-history recordings documenting life in Farm Security Administration migrant worker camps in central California during 1940 and 1941.

## Intended audience
General visitors, students, educators, researchers beginning exploration, and descendants or community members seeking respectful access to the historical record. No specialist archival knowledge may be assumed.

## Required facts and content
The source collection is **Voices from the Dust Bowl: The Charles L. Todd and Robert Sonkin Migrant Worker Collection, 1940 to 1941**, held by the American Folklife Center at the Library of Congress. The collection documents everyday life in FSA migrant work camps in central California. The complete collection includes approximately 18 hours of audio, 28 graphic images, and print materials; the online presentation includes hundreds of audio titles, photographs, and field material.

This benchmark uses only the four frozen records and four frozen image references listed in `fixtures/content/archive.json` and `fixtures/images/manifest.json`. The implementation must not expand the collection with additional people, quotations, recordings, photographs, dates, or claims.

### Approved collection introduction
Between 1940 and 1941, Charles L. Todd and Robert Sonkin recorded conversations, meetings, stories, songs, and daily experience in Farm Security Administration migrant worker camps across central California. This bounded selection follows four voices and public moments across Shafter, El Rio, Visalia, and Yuba City.

### Approved interpretive note
These recordings preserve individual testimony and community activity within a larger federal collecting project. Present the people represented as historical participants, not as visual atmosphere. Keep names, places, dates, source notes, and credit lines attached to their records.

### Approved rights note
The Library of Congress states that it is not aware of U.S. copyright protection or other restrictions in this collection except as noted, while reminding users that privacy, publicity, cultural sensitivity, and item-specific rights may still apply. Every displayed item must retain its Library of Congress source link and credit line.

## Approved copy
All visitor-facing prose is frozen in `fixtures/content/archive.json`. Copy may be arranged, shortened only where the fixture explicitly supplies a short form, or repeated for navigation and accessibility. It may not be paraphrased into stronger historical claims, invented quotations, first-person speech, or fictional captions.

## Available data
Four oral-history records are supplied with: identifier, title, participant or speaker, collectors, date, place, format, topic tags, approved summary, source URL, credit line, and availability note. One collection-level context record is supplied. Filtering may use only the supplied places and topics.

## Approved images and provenance
Four image references are supplied in `fixtures/images/manifest.json`. Each reference includes a Library of Congress item or resource URL, title, creator where known, date, place, credit line, rights note, approved alt text, and approved caption. Do not substitute other imagery, generate replacement imagery, crop away essential people or documentary context, colorize, fabricate missing detail, or apply treatments that imply a different historical source.

## Required routes
1. `/` — collection introduction and an immediate path into listening.
2. `/voices` — all four records with filtering by place or topic.
3. `/voices/augustus-martinez` — a complete record detail page for the Augustus Martinez interview.
4. `/about` — collection context, source, rights, and credits.

Equivalent client-side routing is acceptable if all route URLs are directly reachable and refresh-safe in the chosen runtime.

## Required states
- Default collection introduction.
- Unfiltered voices index.
- Voices index filtered to one place or one topic.
- A no-results response that preserves the visitor's current filter controls and offers a clear reset.
- Augustus Martinez detail with recording metadata and an accessible play/pause control or, when audio bytes are unavailable, a clearly labeled source-listening action.
- Transcript/context disclosure expanded and collapsed; because no transcript text is frozen, the disclosure may contain only the approved source and context note.
- Mobile filter control open and closed.
- Keyboard focus visibly present on all interactive elements.
- Reduced-motion behavior active when requested by the operating system.

## Required actions
Visitors must be able to:
- choose whether to begin by place or by topic;
- filter the four records;
- open the Augustus Martinez record;
- start or stop available audio, or follow the official source-listening action when audio is not locally available;
- open and close contextual information;
- clear filters;
- navigate among all required routes.

The meaningful visitor decision is choosing a listening path by place or topic and selecting a record from that path.

## Accessibility requirements
- Meet WCAG 2.2 AA intent for contrast, focus visibility, keyboard operation, semantic landmarks, heading order, labels, and touch targets.
- Images require the frozen alt text.
- Audio controls require an accessible name, current state, and keyboard operation.
- Do not auto-play audio.
- Do not communicate selected filters, playback state, or errors through color alone.
- Respect `prefers-reduced-motion` and provide no essential information only through animation.

## Responsive requirements
- Preserve information priority at widths from 320px through 1440px.
- The place/topic choice and filter interaction must remain operable with one hand on a 390px-wide viewport.
- No horizontal page overflow at 320px, 390px, 768px, 1024px, or 1440px.
- Long titles, participant names, source labels, and credit lines must wrap without clipping.
- Mobile must recompose the experience rather than merely shrink or mechanically stack desktop regions.

## Prohibited inventions
- No invented quotations, transcript excerpts, biographies, family relationships, emotions, outcomes, statistics, camp conditions, or historical events.
- No additional routes, people, records, places, dates, maps, timelines, donations, memberships, accounts, personalization, recommendations, or social features.
- No generated photography, decorative pseudo-documents, faux archival stamps, simulated handwriting, fake catalog numbers, or invented institutional marks.
- No claim that the benchmark product is operated by the Library of Congress.
- No visible design rationale, implementation status, validation language, condition label, experiment label, or construction aid.

## Evidence requirements
Each condition must produce the evidence named in `experiment.json`, including representative desktop and mobile renders, route/link/state validation, responsive overflow, keyboard/focus, contrast and legibility, reduced motion, content fidelity, isolation, and actual limitations. A static check must not be reported as browser-engine validation.

## Implementation budget
Each condition receives the same budget: one bounded implementation pass; no external UI kits, component libraries, design systems, or starter templates; no source sharing; no more than 15 implementation files; no more than 250 KB of first-party HTML, CSS, and JavaScript before images; and the same required viewport evidence. Existing runtime tooling available equally to all conditions may be used.

## Product-solution boundary
This brief defines content, behavior, accessibility, responsive obligations, and evidence. It does not prescribe composition, components, typography, palette, imagery treatment beyond documentary integrity, visual metaphor, layout system, or historical aesthetic.
