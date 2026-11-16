---
name: lvdash-verbiage-fix
description: Fix the wording in Databricks AI/BI (Lakeview) *.lvdash.json dashboards in a Databricks Asset Bundle's dashboards/ directory - multiple spaces between words, grammar and spelling (Canadian, British and other variants converted to US English), and a professional, narrative tone. Use when asked to clean up, proofread, copy-edit, Americanize or standardize titles, labels, descriptions or text widgets in lvdash.json files or Lakeview dashboards. Writes a fixed copy of the dashboards to dashboard_verbiage_fix/ and a CSV report giving each change's page and location; the originals change only on request. Edits display text only; never touches SQL, field names or data values.
---

# lvdash verbiage fix

Copy-edits the display text in `*.lvdash.json` files. By default it leaves the originals alone and writes a fixed set to `dashboard_verbiage_fix/`, with a CSV report that says where each change is (page, widget title or text heading). A deterministic script handles spacing, US spelling, grammar and tone clean-up; Claude then handles the rewrites a script cannot do (narrative, professional phrasing). Design problems such as colors and layout belong to `lvdash-design-review`.

Rules and examples: [references/style-guide.md](references/style-guide.md).

## Setup

- `SKILL_DIR` means the folder that contains this `SKILL.md` (for example `.claude/skills/lvdash-verbiage-fix` in a project, or `~/.claude/skills/lvdash-verbiage-fix` for a personal install). Run the commands from the bundle root so the `dashboards` path resolves.
- Python 3 only; the script uses the standard library and needs no installs.
- Run `python3 "$SKILL_DIR/scripts/lvdash_text.py" --help` (also `fix --help`) to see the options. The script is large and tested, so do not read its source unless you are debugging it.

## Safety

- Only display text changes. SQL (`queryLines`), `fieldName`, `expression`, ids, colors and category values are never modified.
- By default the originals are never touched. A `fix` dry run writes the full set of dashboards, fixed where needed, to `dashboard_verbiage_fix/` in the current directory, next to `dashboards/`; the user opens or deploys those copies when they are happy with them. `--write` edits the originals in place: use it only when the user asks for that.
- Before any `--write` on the originals, confirm with `git status` that the dashboards are clean or committed, so the edit can be reviewed as a diff. If they are not under version control, copy them first.
- If a dashboard is also edited in the Databricks workspace, tell the user the bundle copy will overwrite those edits on the next deploy.
- Only the changed strings are written; numbers, spacing, indentation, line endings and a BOM stay byte-identical, in the copies and in `--write` alike.

## Workflow

Copy this checklist and tick items off as you go:

```
Progress:
- [ ] 1. Find the files
- [ ] 2. Decide on protected terms (--keep)
- [ ] 3. Dry run: report plus fixed copies in dashboard_verbiage_fix/
- [ ] 4. Judgment pass on the fixed copies
- [ ] 5. Verify the fixed copies
- [ ] 6. Report back
```

1. **Find the files** under the dashboards directory (default `dashboards/`, recursive).
2. **Ask about protected terms** only if the text appears to contain brand or place names the spelling rules would change (for example "Centre Street"). Pass them with `--keep Centre,Colour`.
3. **Dry run the mechanical fixes** and review the output:

   ```bash
   python3 "$SKILL_DIR/scripts/lvdash_text.py" fix dashboards
   ```

   Each change shows the JSON path, where it is on the dashboard (page, then the widget title or the heading of the text box), before, after and the rules applied. The run saves a CSV report named after the dashboards and the date, for example `Sales Dashboards - Wording Fixes (Proposed) - 2026-11-16.csv`, with `page` and `location` columns, and writes the fixed set of dashboards to `dashboard_verbiage_fix/`; the last lines of output give both. Lines marked `REVIEW` need a judgment rewrite; they are only reported on the run that makes the change, so keep this CSV. Look for false fixes (a proper noun re-cased, a product acronym changed) and re-run with `--keep`.
4. **Judgment pass for tone and narrative, on the fixed copies.** List every display string with its path, then read them against the style guide:

   ```bash
   python3 "$SKILL_DIR/scripts/lvdash_text.py" extract dashboard_verbiage_fix -o strings.json
   ```

   Rewrite strings that are terse, vague, slangy or unprofessional, following "Judgment rules" in the style guide: descriptive title-case titles, plain-language labels, narrative one-to-three-sentence descriptions and text widgets that state the insight and why it matters. Keep facts unchanged. Write the rewrites to an edits file with `old` so stale edits are skipped, then dry run, show the user, and write them into the copies:

   ```bash
   python3 "$SKILL_DIR/scripts/lvdash_text.py" apply dashboard_verbiage_fix edits.json
   python3 "$SKILL_DIR/scripts/lvdash_text.py" apply dashboard_verbiage_fix edits.json --write
   ```

   These save `… - Wording Rewrites (Proposed)` and `(Applied)` reports in the same way.
5. **Verify** the copies: re-run `fix` on them without writing; it should report no changes other than remaining `REVIEW` items. Confirm each file is still valid JSON, and compare the copies with the originals (for example `git diff --no-index --stat dashboards dashboard_verbiage_fix`).

   ```bash
   python3 "$SKILL_DIR/scripts/lvdash_text.py" fix dashboard_verbiage_fix --no-report
   ```
6. **Report back** with the report CSVs, the `dashboard_verbiage_fix/` folder, the number of strings changed per file and anything left open. Replacing the originals is the user's call: when they ask, copy the files from `dashboard_verbiage_fix/` over `dashboards/` (after the `git status` check above), or run `fix dashboards --write` and `apply dashboards edits.json --write`.

## Examples

Mechanical fix, dry run output (for a dashboard whose text widget says `LOOK AT MAY!!!` and `We're kinda tracking the colour of money!!`):

```
dashboards/sales.lvdash.json  pages[0].layout[0].widget.spec.frame.title
   at Sales Overview › 'QTLY_REV by region' (bar chart) › title
   - 'QTLY_REV  by region'
   + 'Quarterly REV by Region'   [abbreviation expanded, code-style name, spacing, title case]  REVIEW: ambiguous abbreviation 'REV'
dashboards/sales.lvdash.json  pages[0].layout[1].widget.multilineTextboxSpec.lines[0]
   at Sales Overview › Text box starting 'LOOK AT MAY!!!'
   - 'LOOK AT MAY!!!'
   + 'Look at may.'   [capitalization, punctuation]  REVIEW: check capitalization of 'May', 'March' or 'August' (a month name or an ordinary word)
dashboards/sales.lvdash.json  pages[0].layout[1].widget.multilineTextboxSpec.lines[1]
   at Sales Overview › Text box starting 'LOOK AT MAY!!!'
   - "We're kinda tracking the colour of money!!\n"
   + 'We are somewhat tracking the color of money.\n'   [US spelling, punctuation, tone: contraction expanded, tone: informal wording]

3 change(s), 2 item(s) with a REVIEW note, in 1 file(s); dry run, nothing written (use --write).
Report -> sales - Wording Fixes (Proposed) - 2026-11-16.csv
Fixed copies -> dashboard_verbiage_fix/ (1 file(s), 1 with changes); originals unchanged
```

Both `REVIEW` items need context the script does not have: `REV` here is revenue, and `MAY` is the month. They go to the judgment pass. `REVIEW` notes are only raised on the run that makes the change, so keep the dry-run report CSV (column `needs_review`) for step 4.

Edits file for the judgment pass (`extract` gives the paths and current text). A `file` value can name the original or the copy: when it does not match a scanned path, the unique file name is used.

```json
[{"file": "dashboards/sales.lvdash.json",
  "path": "pages[0].layout[0].widget.spec.frame.title",
  "old": "Quarterly REV by Region",
  "new": "Quarterly Revenue by Region"},
 {"file": "dashboards/sales.lvdash.json",
  "path": "pages[0].layout[1].widget.multilineTextboxSpec.lines[0]",
  "old": "Look at may.",
  "new": "Revenue spiked in May after the new marketing campaign launched."}]
```

A `file` value can be a full or relative path; a bare file name must be unique among the scanned files or the edit is skipped as ambiguous.

## Options

- `fix --keep Word1,Word2`: leave words untouched.
- `fix --no-tone`: spacing, spelling and grammar only (contractions, informal words and filler stay).
- `fix --no-titlecase`: do not re-case titles.
- `fix --copies-dir DIR`: write the fixed copies somewhere other than `dashboard_verbiage_fix/`; `fix --no-copies`: no copies.
- `fix`/`apply --report file.csv`: choose the report name; `--no-report`: write no report. A default name that already exists gets ` (2)`, ` (3)` rather than being overwritten.
- `extract -o file`: write all display strings with kind (`title`, `label`, `description`, `text`) to a file.
- Exit code: 0 on success; 1 if any file was skipped because it was not valid UTF-8 JSON (other files are still processed). A missing path or an empty folder is an error.

## Limits

- Grammar fixes are rule-based: a/an, duplicate words, capitalization, terminal periods, common typos. They do not parse sentences, so subject-verb agreement, tense and clause structure are handled in the judgment pass.
- Ambiguous abbreviations (Rev, Reg, Cat, Val) are flagged, not expanded, because the right word depends on the dataset.
- Text widgets keep their markdown structure: headings, lists, links and images, code spans, fenced and indented code blocks (left untouched), table rows (only the cell text is fixed), raw HTML lines and two-space line breaks.
