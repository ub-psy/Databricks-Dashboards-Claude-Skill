# Wording style guide for dashboard text

Based on dashboard typography, labeling and annotation practice and US business-writing norms. Self-contained: no other document is needed.

## What counts as user-facing text

Edited: page names (`pages[].displayName`), widget titles and descriptions (`spec.frame.title`, `spec.frame.description`),
axis, legend and column labels (`displayName`, `title` inside `encodings`), text-widget markdown
(`multilineTextboxSpec.lines[]`), dataset display names (hygiene only).

Never edited: `queryLines` (SQL), `fieldName`, `expression`, `name` ids, `datasetName`, color values, category
`value` strings in `mappings`, `scale`, `format`, URLs, backtick code, `{{parameters}}`.

## Mechanical rules (applied by `lvdash_text.py fix`)

| Area | Rule |
|---|---|
| Spacing | One space between words; no space before `, . ; : ! ?`; a space after commas and sentence ends; no padding inside parentheses; no leading or trailing spaces. Markdown indentation and a deliberate two-space line break are kept. |
| Spelling | US English: colour to color, centre to center, analyse to analyze, organisation to organization, labelled to labeled, grey to gray, whilst to while, programme to program, and so on. Common typos corrected. |
| Grammar | Duplicate words removed ("the the"); a/an agreement; sentence-initial capital; standalone "i" to "I"; full sentences in descriptions and paragraphs end with a period; `&` becomes "and". |
| Titles | Title case (small words such as of, by, and the stay lowercase, except first and last); no ALL CAPS; snake_case and camelCase become spaced words; unambiguous abbreviations expanded (Qtly to Quarterly, Amt to Amount). Acronyms (KPI, YTD, SQL, FY25) keep their case. |
| Tone | Contractions expanded (do not, it is); informal words replaced (kinda to somewhat); filler such as "really", "very", "basically" removed; exclamation marks become periods; emoji removed; shouting (ALL CAPS) lowercased to sentence or title case. |

Use `--keep Word1,Word2` for brand names or proper nouns that must be left alone (for example a place called "Centre Street").

## Judgment rules (done by Claude, then applied with `apply`)

The script flags these with `REVIEW`; it does not rewrite them.

1. **Professional.** No slang, hype or vague words (awesome, huge, stuff, things, a lot). Replace with a precise, plain term. No humor, no second-person chatter.
2. **Narrative.** Text widgets and descriptions say what the viewer is looking at and why it matters, in complete sentences, active voice, present tense. Lead with the insight, then the context. One to three sentences; the guide limits annotations to 1-3 per chart and "a sentence or less" for each callout.
   - Weak: `rev by reg q1`
   - Better title: `Quarterly Revenue by Region (Q1 2025)`
   - Weak description: `shows sales`
   - Better description: `Revenue by region for the current quarter, ranked highest to lowest, to show where growth is concentrated.`
   - Weak callout: `LOOK AT MAY!!!`
   - Better callout: `Revenue spiked in May after the new marketing campaign launched.`
3. **Titles.** Descriptive and specific: what is measured, for whom, and the period when relevant. Spell out abbreviations. Under about 60 characters. Ambiguous abbreviations (Rev, Reg, Val, Cat, Desc, Num, Prod) need the dataset context to expand correctly.
4. **Labels.** Axis and column labels are short readable names with units where helpful (`Total Revenue ($M)`). Hide an axis title instead of repeating the chart title.
5. **Consistency.** Same term for the same concept on every page (customer vs client), one case convention for titles, one voice across text widgets.
6. **Facts are fixed.** Never invent figures, causes, dates or business meaning. If a rewrite would need a fact you do not have, keep the original wording, fix only the mechanics, and list it as an open question.
