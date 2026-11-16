# Dashboard skills for Claude Code

Two Claude Code skills for **Databricks AI/BI (Lakeview) dashboards**, the `*.lvdash.json` files you keep in a Databricks Asset Bundle (usually in a `dashboards/` folder).

| Skill | What it does | Changes your dashboards? |
|---|---|---|
| `lvdash-design-review` | Reviews each dashboard against dashboard design best practices (color, typography and labeling, layout, annotations, accessibility, interactivity and storytelling) and writes an Excel report of suggestions, each with the page and widget it applies to | No, read-only |
| `lvdash-verbiage-fix` | Cleans up the wording: extra spaces, grammar, US spelling (Canadian and British variants converted) and a professional, narrative tone. Writes a fixed copy of your dashboards to `dashboard_verbiage_fix/` and a CSV report of every change | No, unless you ask it to update the originals |

Both skills are self-contained: their rules live in the skill folders, so they need no other document, service or API key.

## Requirements

- Claude Code.
- **Python 3.9 or later.** The wording skill uses only the standard library. The design review also needs `openpyxl`:

  ```bash
  python3 -m pip install -r requirements.txt
  ```
- **Git** (recommended), so you can review any change to your dashboards as a diff.

## Install

Choose where the skills should be available:

- **One project.** Copy the two skill folders into the `.claude/skills/` folder of the repository that holds your dashboards, and commit them so everyone who clones it gets the skills:

  ```bash
  mkdir -p /path/to/your-bundle/.claude/skills
  cp -R .claude/skills/lvdash-design-review .claude/skills/lvdash-verbiage-fix /path/to/your-bundle/.claude/skills/
  ```

- **All your projects.** Copy them to your personal skills folder:

  ```bash
  mkdir -p ~/.claude/skills
  cp -R .claude/skills/lvdash-design-review .claude/skills/lvdash-verbiage-fix ~/.claude/skills/
  ```

- **Just to try them.** Open Claude Code in this repository; the skills load from its `.claude/skills/` folder.

Restart Claude Code if it was already running, type `/` and check that both skills are listed.

## Try it on the sample dashboard

`examples/dashboards/sales_overview.lvdash.json` is a small made-up dashboard with typical problems: a code-style title, red next to green, raw field names as labels, an unlabeled filter, a filter that opens pre-set, KPIs without a period, British spelling and an informal tone.

```bash
cd examples
claude
```

Then ask:

```
/lvdash-design-review review the dashboards in dashboards/
/lvdash-verbiage-fix clean up the wording in dashboards/
```

## Using the design review

Open Claude Code in the folder that contains `dashboards/` and ask in plain language, for example "review my Lakeview dashboards for design best practices", or run the skill by name:

```
/lvdash-design-review review the dashboards in dashboards/
```

Claude runs the automated checks, looks for false positives, adds judgment points a script cannot catch (for example a chart type that does not suit the data) and summarizes the top suggestions per dashboard. The dashboards are never edited.

**The report** is an Excel workbook named after your dashboards and the date, for example `Sales Dashboards - Design Review - 2026-11-16.xlsx`. A second run on the same day adds ` (2)` instead of overwriting.

| Sheet | What it holds |
|---|---|
| Read me | What the report is and how to use it. Everything in it is a **suggestion** for the dashboard owner to consider, not an error |
| Summary | One row per dashboard: a rough score (100 minus 10 per High, 4 per Medium and 1 per Low suggestion) and counts by priority and category |
| Suggestions | One row per suggestion: page, widget, what was found, the suggested change, the guideline behind it and the JSON path. Status starts as "To consider"; set it to Accepted, Done or Not applicable as you go |
| Manual review | Checks that need a person to look at the rendered dashboard, condensed: one row for the whole dashboard, then per page a row about the page and a row about its charts, each naming the charts, filters or images it covers |
| Rules | Every rule with its guideline in one sentence |

**Finding things.** Every suggestion names its page and widget the way a user sees them: by title, or for an untitled widget by its type, the text directly above it and its grid position, for example *Untitled bar chart under 'Ownership Optimism' at column 1, row 6*. Suggestions that span pages, such as one category shown in two colors, list every page and widget involved.

**Priority.** High is likely to mislead or exclude readers (overlapping widgets, red next to green, more than 12 visuals on a page). Medium weakens clarity (missing or raw titles, inconsistent colors, unlabeled filters). Low is polish.

**What is checked.** 33 automated rules and 10 manual checks:

| Area | Examples |
|---|---|
| Color | Too many colors, rainbow scales, red with green, low contrast, one category in different colors |
| Typography and labeling | Missing, generic or code-style titles, raw field names as labels, mixed title case, long text boxes, too many or decorative fonts |
| Layout | Overlaps, widgets off the 12-column grid, uneven rows, crowded pages, key numbers below charts, filters below content |
| Annotations | Pages without a takeaway, too many text boxes, no overview on the first page |
| Accessibility | Charts without a description, images without alt text |
| Interactivity | Too many filters, unlabeled filters, filters that open pre-set |
| Storytelling | KPIs that do not name their period, pages that open with a chart instead of the takeaway |

The full rule list is in [`.claude/skills/lvdash-design-review/references/guidelines.md`](.claude/skills/lvdash-design-review/references/guidelines.md). Images and logos are never treated as charts.

## Using the wording fix

```
/lvdash-verbiage-fix clean up the wording in dashboards/ - US English, no double spaces, professional tone
```

Other ways to ask: "proofread the text in my lvdash.json files", "convert the dashboard text to US spelling".

Claude works in two stages:

1. **Mechanical fixes** by script: spacing, punctuation, US spelling (colour to color, centre to center), common typos, a/an, repeated words, capitalization, title case, contractions, filler words and exclamation marks.
2. **Judgment rewrites** by Claude: terse, vague or informal text becomes descriptive titles, plain-language labels and short narrative descriptions. Facts are never invented; anything that needs context Claude does not have is listed as an open question.

**What you get**

- `dashboard_verbiage_fix/`: a complete copy of your dashboards, fixed where needed, with the same file names, next to `dashboards/`. **Your originals are not changed.** Open, compare or deploy the copies when you are happy with them.
- A CSV report, for example `Sales Dashboards - Wording Fixes (Proposed) - 2026-11-16.csv`, with one row per change: the page, the location in plain words (for example `'Revenue by Region' (bar chart) › title` or `Text box, under heading 'Key Findings'`), the JSON path, the text before and after, the rules applied and anything flagged for review.

Only display text is touched: page names, widget titles and descriptions, axis and column labels, and text-box markdown. SQL, field names, expressions, ids, colors, data values and HTML tags are never changed, and the rest of each file stays byte-identical.

**Compare and replace.** See what changed with:

```bash
git diff --no-index --stat dashboards dashboard_verbiage_fix
```

To update the originals, copy the files over, or ask Claude to write the changes in place. Commit first so the edit is a reviewable diff. If someone also edits the same dashboard in the Databricks workspace, the next `bundle deploy` overwrites their edits with the bundle copy.

Tell Claude about brand or place names that the spelling rules should leave alone (for example "Centre Street"); it passes them to the script with `--keep`.

## Running the scripts without Claude

Both skills are thin wrappers around Python scripts, so they also work on their own, for example in CI. Run them from the folder that contains `dashboards/`:

```bash
# Design review: writes '<dashboards> - Design Review - <date>.xlsx' (-o to choose the name)
python3 .claude/skills/lvdash-design-review/scripts/assess_lvdash.py dashboards

# Wording fix, dry run: writes dashboard_verbiage_fix/ and '<dashboards> - Wording Fixes (Proposed) - <date>.csv'
python3 .claude/skills/lvdash-verbiage-fix/scripts/lvdash_text.py fix dashboards

# Change the originals in place instead (report saved as '(Applied)')
python3 .claude/skills/lvdash-verbiage-fix/scripts/lvdash_text.py fix dashboards --write

# List every display string with its JSON path; apply reviewed rewrites from an edits file
python3 .claude/skills/lvdash-verbiage-fix/scripts/lvdash_text.py extract dashboards -o strings.json
python3 .claude/skills/lvdash-verbiage-fix/scripts/lvdash_text.py apply dashboard_verbiage_fix edits.json --write
```

| Wording option | Effect |
|---|---|
| `--write` | Change the original files in place (the default is a dry run) |
| `--copies-dir DIR` | Write the fixed copies to `DIR` instead of `dashboard_verbiage_fix/` |
| `--no-copies` | Do not write fixed copies |
| `--report file.csv` | Choose the report name |
| `--no-report` | Do not write a report |
| `--keep Word1,Word2` | Leave these words unchanged |
| `--no-tone` | Spacing, spelling and grammar only; keep contractions, informal words and filler |
| `--no-titlecase` | Do not re-case titles |

An edits file for `apply` is a JSON list; `old` makes an edit skip if the text has changed since you reviewed it:

```json
[{"file": "dashboards/sales.lvdash.json",
  "path": "pages[0].layout[0].widget.spec.frame.title",
  "old": "Quarterly REV by Region",
  "new": "Quarterly Revenue by Region"}]
```

Exit codes: `0` on success; `1` if a file was skipped because it was not valid JSON (the others are still processed). Run any script with `--help` for all options.

### Example: design review in GitHub Actions

The design review can run on every pull request that touches a dashboard and attach the report to the run. This uses the script only, so no Claude credentials are needed. It assumes the skills are committed under `.claude/skills/` in the bundle repository.

```yaml
name: Dashboard design review
on:
  pull_request:
    paths: ["dashboards/**.lvdash.json"]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install openpyxl
      - run: python .claude/skills/lvdash-design-review/scripts/assess_lvdash.py dashboards -o design-review.xlsx
      - uses: actions/upload-artifact@v4
        with:
          name: dashboard-design-review
          path: design-review.xlsx
```

## Suggested order

1. Run the **design review** to see structural and visual issues.
2. Run the **wording fix** and review the report and the copies in `dashboard_verbiage_fix/`.
3. Re-run the design review on `dashboard_verbiage_fix/`: title and label suggestions should be gone; layout and color suggestions stay until you change the dashboard.
4. Work through the Manual review sheet on the rendered dashboard.

## Limits

- The design review reads the JSON, not the rendered dashboard. It cannot see theme fonts, the real data, whether a chart type suits it, or how colors look together; those items are on the Manual review sheet. Treat the report as a prioritized list of suggestions, not a verdict.
- Lakeview widget specs vary by version. The scripts tolerate missing or unexpected keys; an empty report means nothing was detected, not that a dashboard is perfect.
- Grammar fixes are rule-based (a/an, repeated words, capitalization, punctuation, common typos). Sentence-level rewrites are left to Claude's judgment pass.

## Repository layout

```
.claude/skills/
  lvdash-design-review/
    SKILL.md                    instructions Claude follows
    scripts/assess_lvdash.py    the automated review (writes the Excel report)
    references/guidelines.md    the rule catalog
  lvdash-verbiage-fix/
    SKILL.md
    scripts/lvdash_text.py      the wording fixer (fix, extract, apply)
    references/style-guide.md   the wording rules
examples/dashboards/            a sample dashboard to try the skills on
requirements.txt                openpyxl, for the design review
```
