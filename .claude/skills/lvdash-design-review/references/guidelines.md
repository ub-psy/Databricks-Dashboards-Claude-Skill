# Dashboard visualization guidelines (rule reference)

Self-contained rule catalog for dashboard design: no other document is needed to apply it. Every rule ID below is
emitted by `scripts/assess_lvdash.py` or is a manual check listed on the report's "Manual review" sheet. The report's
"Guideline" column restates the rule in a sentence, so findings can be read on their own.

## Color

| Rule | Guideline | Automated check on lvdash.json |
|---|---|---|
| COL-01 | One accent color for what matters, muted tones elsewhere; too many colors is noise | A widget uses more than 8 distinct colors or color mappings; the dashboard uses more than 12 distinct hex colors |
| COL-02 | Avoid rainbow gradients; use sequential or diverging palettes | A `scheme` named rainbow/jet/spectral/turbo, or a continuous `colorRamp` spanning 4+ hue families (categorical palettes are not ramps) |
| COL-03 | Do not rely on red vs green; add redundancy for color-blind viewers, roughly 1 in 12 men and 1 in 200 women | Widget pairs a saturated red with a saturated green |
| COL-04 | Keep contrast high; distinguishable marks | Mark colors with contrast below 2:1 against white, or two saturated colors that are very close |
| COL-05 | Same meaning, same color, across every chart | A category value mapped to different colors in different widgets |
| COL-06 | Categorical palettes hold up to about 6-8 groups | Categorical scale with more than 8 mappings |
| COL-M1 | Palette matches audience tone, culture, brand and data literacy | Manual, once per dashboard |
| COL-M2 | Meaning carried by more than color; tested in a color-blind simulator | Manual, once per chart that uses color |

## Typography and labeling

| Rule | Guideline | Automated check |
|---|---|---|
| TYP-01 | Every chart has a descriptive, readable title of its own; spell things out | Chart, table or counter without a visible title (titles stored as text or as `{"value": ...}`, and a custom chart's Vega title, count). Medium when nothing labels it; Low when a heading directly above it acts as its title. Images, text boxes and filters are never flagged |
| TYP-02 | Titles: title case, no snake_case, no ALL CAPS, no unclear abbreviations, not too long | Placeholder or generic title, snake/camel case, ALL CAPS, ambiguous or clipped abbreviations (Qtly, Rev, Amt; not standard ones such as vs or YTD), over 60 characters |
| TYP-03 | Consistent case across titles | Mix of title case and sentence case among titles |
| TYP-04 | Axis and column labels are readable names, not raw field names | Display names or field names in snake_case, camelCase, backticks or aggregate form such as `sum(amount)`; units in parentheses such as `Revenue ($M)` are fine |
| TYP-05 | Do not overload text; hierarchy by size and weight | Text widget over 500 characters or 8 lines; ALL CAPS paragraphs; several top-level headings |
| TYP-06 | Avoid clutter in tables and dense plots | Table with more than 10 columns |
| TYP-07 | One or two clean sans-serif fonts at readable sizes | Text boxes set more than two font families, a serif, script or monospace family, or text below 12px |
| TYP-M1 | One or two sans-serif fonts; 24pt+ titles, 14-18pt axes, 10-12pt body | Manual, once per dashboard (theme-level) |
| TYP-M2 | Legend near the data, or direct labels for few series; label outliers only; tooltips for detail | Manual, once per chart with a legend |

## Layout and visual structure

| Rule | Guideline | Automated check |
|---|---|---|
| LAY-01 | Elements do not overlap | Overlapping widget rectangles on a page |
| LAY-02 | Content snaps to the 12-column grid | Widget extends beyond column 12 |
| LAY-03 | Same-size cards in a row; consistent heights | Widgets that start on the same row with different heights, unless the shorter one has another widget stacked directly beneath it (images such as logos are ignored) |
| LAY-04 | Balanced rows with even margins; no ragged gaps | Grid columns left empty in a band of rows, measured on the full widget rectangles (one finding per band) |
| LAY-05 | White space; do not jam many charts on one page | More than 8 visualizations on a page (High above 12) |
| LAY-06 | Key metrics first, with more weight | Counters placed below charts; several equal-sized counters with no emphasis |
| LAY-07 | Filters grouped at the top | Filter widgets placed below content |
| LAY-08 | Charts get enough room to be read | Visualization narrower than 3 columns or shorter than 4 rows |
| LAY-09 | Readable page names | Generic or machine-style page display names |
| LAY-M1 | Consistent gutters of about 12-24 px; 16 px between title and plot | Manual, once per page |

## Axes, gridlines, legends and annotations

| Rule | Guideline | Automated check |
|---|---|---|
| ANN-01 | Annotate the main insight; 1-3 annotations per chart or page | Page with 3+ visualizations and no text widget |
| ANN-02 | Do not overdo annotations | More than 3 text boxes on one page (each is listed) |
| ANN-03 | A dashboard opens with a title or overview | First page has no title/overview text widget |
| AXS-M1 | Short axis labels (1M not 1,000,000), light gray, soft or dashed gridlines, few of them | Manual, once per chart with axes |

## Accessibility

| Rule | Guideline | Automated check |
|---|---|---|
| ACC-01 | Every chart has a short description stating what it shows and its takeaway, so the insight does not depend on seeing the chart | Chart with no description shown (`showDescription` off or empty) |
| ACC-02 | Images that carry information need alternative text | Markdown image with empty `![]`, or HTML `<img>` without `alt`, in a text box |
| ACC-M1 | Decorative images (logos) need nothing; informative images need their message in nearby text | Manual, once per image |

## Interactivity

| Rule | Guideline | Automated check |
|---|---|---|
| INT-01 | Offer only the filters the audience needs; every control hands part of the story to the user | More than 3 filters on a page (Medium above 5) |
| INT-02 | Every filter has a clear label in the audience's terms | Filter without a visible title |
| INT-03 | Open with a sensible default view so every user starts from the same complete picture | Multi-select or date filter that opens with a preset selection (single-select filters need one, so they are not flagged) |
| INT-M1 | The main message stays visible whatever the filters are set to, and the way back to the default view is obvious | Manual, once per page with filters |

## Storytelling

| Rule | Guideline | Automated check |
|---|---|---|
| STY-01 | Name the measure, unit and period so a number cannot be misread | Counter whose title and description name no period (day, month, quarter, YTD, a year, "last 30 days" and so on) |
| STY-02 | Each page leads with its main takeaway, not just its charts | Page whose first element is a chart, with all text below it |
| STY-M1 | Know the audience; choose the format (monitoring dashboard, one-off visual or guided story) and density for them | Manual, once per dashboard |
| STY-M2 | Each page has a hook, an insight and an impact, and the key message is seen first | Manual, once per page |

## Locations

Every suggestion names its page and widget. A widget with a title is named by it; an untitled one by its type, the text directly above it and its grid position (column 1-12 from the left, row from the top). Suggestions that span pages (COL-01, COL-05, TYP-03, TYP-07) list every page and widget involved. On the Manual review sheet the checks are grouped: one row for the dashboard (STY-M1, COL-M1, TYP-M1), and per page one row for the page (STY-M2, LAY-M1, INT-M1, ACC-M1) and one for its charts (COL-M2, TYP-M2, AXS-M1), naming the widgets each check covers.
