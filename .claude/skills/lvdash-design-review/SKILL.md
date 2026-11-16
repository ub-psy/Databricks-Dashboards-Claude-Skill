---
name: lvdash-design-review
description: Assess Databricks AI/BI (Lakeview) *.lvdash.json dashboards in a Databricks Asset Bundle's dashboards/ directory against dashboard design best practices (color, typography and labeling, layout, annotations, accessibility, interactivity, storytelling) and produce an Excel report of suggested changes for the dashboard owner, with the page and widget for each one. Use when asked to review, audit, score, critique or give design feedback on lvdash.json files, Lakeview or AI/BI dashboards, or a DAB dashboards folder. Read-only; does not edit the dashboards.
---

# lvdash design review

Reviews each `*.lvdash.json` under a dashboards directory against dashboard design best practices and writes an Excel workbook of **suggestions** for the dashboard owner to consider. It never edits the dashboard files. To fix wording, use the `lvdash-verbiage-fix` skill.

## Setup

- `SKILL_DIR` means the folder that contains this `SKILL.md` (for example `.claude/skills/lvdash-design-review` in a project, or `~/.claude/skills/lvdash-design-review` for a personal install). Run the commands from the bundle root so the `dashboards` path resolves.
- Python 3 with `openpyxl`. If the script stops with "openpyxl is required", run `python3 -m pip install openpyxl`. Use whichever Python environment the project already uses.
- Run `python3 "$SKILL_DIR/scripts/assess_lvdash.py" --help` to see the options. The script is large and tested, so do not read its source unless you are debugging it.

## Inputs

- A dashboards directory (default `dashboards/`, searched recursively) or a single `.lvdash.json`.
- Output path for the workbook (optional). By default the report is named after the dashboards and the date, in the current directory: `Finance Dashboards - Design Review - 2026-11-16.xlsx` for files whose names share "Finance", `sales - Design Review - 2026-11-16.xlsx` for a single file. A second run on the same day adds ` (2)` rather than overwrite. Use `-o` only if the user asks for a specific name.

## Workflow

Copy this checklist and tick items off as you go:

```
Progress:
- [ ] 1. Locate the dashboard files
- [ ] 2. Run the automated assessment
- [ ] 3. Check the Suggestions sheet for false positives
- [ ] 4. Work through the Manual review sheet
- [ ] 5. Add judgment suggestions the script cannot detect
- [ ] 6. Report back
```

1. **Locate the files.** Confirm the directory exists and list its `*.lvdash.json` files. A DAB usually keeps them under `dashboards/` or `src/`; the bundle's `resources/*.yml` shows each `file_path`.
2. **Run the automated assessment:**

   ```bash
   python3 "$SKILL_DIR/scripts/assess_lvdash.py" dashboards
   ```

   It prints `Reviewed N file(s), M suggestion(s) -> <workbook>`. A missing path, an empty folder or a missing output folder stops with a clear message.
3. **Check the Suggestions sheet** against the JSON before reporting. The script is heuristic: it reads layout, titles, labels, filters, text and explicit colors, but cannot see rendered output, theme fonts or the data. If a suggestion is plainly a false positive, set its Status to "Not applicable" and say why in your report. Do not delete rows.
4. **Work through the "Manual review" sheet.** It holds the checks a script cannot make, condensed: one row for the whole dashboard, then for each page one row about the page (takeaway, spacing, filters, images) and one about its charts (color-blind safety, legends and labels, axes). Each row lists its checks once, numbered, names the charts it covers at the top, and marks with "Only:" a check that applies to fewer of them. If a rendered export or screenshot is available, inspect those places and record a result per row, naming any chart that fails in Notes; otherwise leave "To review" and say these remain open.
5. **Add judgment suggestions** using [references/guidelines.md](references/guidelines.md). Typical ones: a chart type that does not suit the data, a pie with many slices, dual axes, missing direct labels, a headline that should be a counter, a page that does not state its takeaway. Append them to the Suggestions sheet with the same columns, rule id `MAN-01`, `MAN-02` and so on, and name the page and widget the way the sheet does.
6. **Report back** with the workbook path, the per-file scores and the top suggestions per file. Present them as suggestions for the owner to act on, not as errors. State which checks were automated and which were judgment.

## Example

A suggestion row (Suggestions sheet):

| File | Page | Widget | Category | Rule | Priority | What was found | Suggested change | Guideline | JSON path |
|---|---|---|---|---|---|---|---|---|---|
| dashboards/sales.lvdash.json | Overview | 'QTLY_REV by Reg' (bar chart) | Typography and labeling | TYP-02 | Medium | Title 'QTLY_REV by Reg': code-style name; abbreviations (qtly, reg, rev). | Spell it out, use title case, and make it descriptive but under about 60 characters. | Titles in title case, spelled out, without code-style names, and under about 60 characters. | pages[0].layout[0].widget.spec.frame.title |

A widget without a title is named by its type, the text directly above it and its grid position, for example `Untitled bar chart under 'Ownership Optimism' at column 1, row 5`. A suggestion that spans pages lists every page and widget involved, for example the charts that show one category in different colors.

A report-back summary:

```
Reviewed 3 dashboards -> Sales Dashboards - Design Review - 2026-11-16.xlsx (suggestions for the owner to consider)
sales.lvdash.json   score 68  (2 High, 9 Medium, 7 Low)  top suggestions: separate overlapping widgets, replace the red/green pair, readable axis labels
ops.lvdash.json     score 92  (0 High, 2 Medium, 0 Low)
Automated: 33 rules. Reviewed by judgment: chart-type fit on sales page 1. Still open: 7 manual review rows (dashboard, pages, charts).
```

## Report layout

| Sheet | Contents |
|---|---|
| Read me | States that the report holds suggestions, not errors, and explains each sheet, priority and status |
| Summary | One row per file: a rough score (100 minus 10 per High, 4 per Medium, 1 per Low), counts by priority and by category |
| Suggestions | One row per suggestion: file, page, widget, category, rule, priority, what was found, suggested change, guideline, JSON path, status (starts as "To consider") |
| Manual review | Checks that need a human look, condensed: one row for the dashboard, then a page row and a charts row per page, each with numbered checks and the charts, filters or images they apply to |
| Rules | Rule catalog with a one-sentence guideline per rule, and where each manual check applies |

Priority: **High** is likely to mislead or exclude readers (overlap, red-green pairing, more than 12 visuals on a page); **Medium** weakens clarity (missing or raw titles, inconsistent colors, uneven rows, unlabeled filters); **Low** is polish.

## What is checked

Rule ids and their guidelines are in [references/guidelines.md](references/guidelines.md), which is self-contained: COL (color), TYP (typography and labeling), LAY (layout on the 12-column Lakeview grid), ANN (annotations), ACC (accessibility), INT (interactivity) and STY (storytelling). Images, and text boxes that hold only images, are treated as images, never as charts. Each suggestion carries the JSON path so the change can be made precisely.

## Notes

- Lakeview specs vary by widget version. The script tolerates missing or malformed keys; an empty Suggestions list for a file means nothing was detected, not that the dashboard is perfect.
- A file that is not valid JSON, or whose structure cannot be read, produces an `ERR-01` row for that file and the review continues with the others.
- Do not rewrite titles or labels here. Suggest the wording in the report and let `lvdash-verbiage-fix` apply it.
- Keep suggestions specific: name the page, the widget, the current value and the target value.
