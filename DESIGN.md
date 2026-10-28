# ScholarAgent design system

## Direction
Research atelier: the quiet working space between a university reading room and a contemporary document editor. Product interface, not a promotional landing page. The user delegated the direction for a complete replacement of the previous dark cockpit.

## First viewport
240px library rail, restrained utility header, spacious question-led workspace. A large Newsreader heading leads directly into a single composer. Configuration is progressively disclosed in a native dialog; eight providers never become eight decorative cards. Suggested questions are editorial rows. The signature is a continuous question-to-document experience: the same workspace becomes a progress journal, then a reader with an inspectable evidence margin.

## System
Canonical runtime tokens: `src/static/app.css` `:root` and `[data-theme=dark]`. Light default: paper #f8f9f6, panel #ffffff, ink #252b27, secondary #626a64, olive #405749, line #dfe3dc. Dark reading mode uses equivalent semantic roles, not inverted images. Manrope for UI and Newsreader for editorial headings and reports, self-hosted under `src/static/fonts` with OFL licenses. No external font dependency.

## Layout and rhythm
Rail 240px, content max 1080px, question area max 760px, reading prose max 70ch. Spacing roles 4/8/12/16/24/32/48/64px. Mobile below 760px uses a compact header and an accessible navigation dialog; composer controls wrap. Document tables scroll within their own wrapper.

## Controls and motion
Single authored SVG stroke vocabulary. Native selects, buttons and dialogs. Corners: 8px for controls, 16px composer and panels. Focus rings olive, immediate pressed feedback, 160–220ms transitions, one brief workspace entrance, no looping ornament. Reduced motion disables nonessential movement. No emoji icons, gradients, neon status pills, fake scores or fabricated recent activity.

## Screens
Home: question and suggested starting points. Research: ordered, truthful execution stages and a readable event journal. Report: document, evidence, sources and process tabs; bibliography and exact passages preserve provenance. Library: searchable real jobs with explicit loading/empty/failure states. Settings: provider/model credentials and research preferences; credentials remain in tab memory.

## References
The user's references informed restraint, responsive press feedback, interruptible transitions, typography and anti-template discipline: impeccable.style, tasteskill.dev, emilkowal.ski/skill, UI Skills apple-design, uupm.cc. The aesthetic is a web implementation, not an official Apple design system.
