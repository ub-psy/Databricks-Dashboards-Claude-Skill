#!/usr/bin/env python3
"""Assess Databricks AI/BI (Lakeview) *.lvdash.json files against dashboard design
guidelines and write an Excel report of suggested changes for the dashboard owner to consider.

Usage:
    python assess_lvdash.py <dashboards_dir> [-o report.xlsx]

Without -o the report is named after the dashboards and the date, for example
"Sales Dashboards - Design Review - 2026-11-16.xlsx", in the current directory.

Read-only: never modifies the dashboard files. Requires openpyxl.
"""
import argparse, colorsys, datetime, json, re, sys
from collections import defaultdict
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
except ImportError:
    sys.exit("openpyxl is required: pip install openpyxl")

GRID = 12   # Lakeview canvas is 12 columns wide
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
ABBREV = {"qtly", "qty", "rev", "amt", "cnt", "avg", "tot", "num", "pct", "yr", "mth", "wk", "reg", "cust",
          "prod", "dept", "mgr", "nbr", "desc", "val", "cat", "grp"}   # only ambiguous or clipped forms; vs, ytd, kpi are standard
GENERIC = re.compile(r"^(untitled|chart|widget|visualization|table|new|page|counter|text)( ?\d*)$", re.I)
RAW_A = re.compile(r"[A-Za-z0-9]_[A-Za-z0-9]|^[a-z]{3,}[A-Z]|`")
AGG_FUNC = re.compile(r"\b(?:sum|avg|count|countdistinct|min|max|median|stddev|first|last)\s*\(", re.I)
SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "vs", "per", "with", "from"}

GUIDE = {  # rule -> (category, guideline); the rule catalog is self-contained, see references/guidelines.md
    "COL-01": ("Color", "One accent color for what matters, muted tones elsewhere; too many colors is noise."),
    "COL-02": ("Color", "Use sequential or diverging palettes, not rainbow gradients."),
    "COL-03": ("Color", "Do not rely on red vs green; add redundancy for color-blind viewers."),
    "COL-04": ("Color", "Keep contrast high so marks stay distinguishable."),
    "COL-05": ("Color", "Same meaning, same color, across every chart."),
    "COL-06": ("Color", "Categorical palettes hold up to about 6-8 groups."),
    "TYP-01": ("Typography and labeling", "Every chart has a descriptive, readable title."),
    "TYP-02": ("Typography and labeling", "Titles in title case, spelled out, without code-style names, and under about 60 characters."),
    "TYP-03": ("Typography and labeling", "Use one case convention for all titles."),
    "TYP-04": ("Typography and labeling", "Axis and column labels are readable names, not raw field names."),
    "TYP-05": ("Typography and labeling", "Do not overload text; build hierarchy with size and weight."),
    "TYP-06": ("Typography and labeling", "Avoid clutter in tables and dense plots."),
    "LAY-01": ("Layout", "Elements do not overlap."),
    "LAY-02": ("Layout", "Content snaps to the 12-column grid."),
    "LAY-03": ("Layout", "Cards in a row share the same height."),
    "LAY-04": ("Layout", "Balanced rows with even margins and no ragged gaps."),
    "LAY-05": ("Layout", "Leave white space; do not jam many charts onto one page."),
    "LAY-06": ("Layout", "Key metrics come first, with more visual weight."),
    "LAY-07": ("Layout", "Group filters at the top."),
    "LAY-08": ("Layout", "Give each chart enough room to be read."),
    "LAY-09": ("Layout", "Give pages readable names."),
    "ANN-01": ("Annotations", "Annotate the main insight, with 1-3 annotations per chart or page."),
    "ANN-02": ("Annotations", "Do not overdo annotations."),
    "ANN-03": ("Annotations", "Open the dashboard with a title or overview."),
    "TYP-07": ("Typography and labeling", "Use one or two clean sans-serif fonts at readable sizes."),
    "ACC-01": ("Accessibility", "Give every chart a short description so the insight does not depend on seeing the chart."),
    "ACC-02": ("Accessibility", "Images that carry information need alternative text."),
    "INT-01": ("Interactivity", "Offer only the filters the audience needs; every control hands part of the story to the user."),
    "INT-02": ("Interactivity", "Every filter has a clear label in the audience's terms."),
    "INT-03": ("Interactivity", "Open with a sensible default view so every user starts from the same complete picture."),
    "STY-01": ("Storytelling", "Name the measure, unit and period so a number cannot be misread."),
    "STY-02": ("Storytelling", "Each page leads with its main takeaway, not just its charts."),
}
MANUAL = [  # (rule, category, scope, check); scope says where the check applies, so each row names its location
    ("STY-M1", "Storytelling", "dashboard", "Who is the audience, and does the dashboard answer their question? Is this the right format (monitoring dashboard, one-off visual or guided story) and the right density for them?"),
    ("COL-M1", "Color", "dashboard", "Does the palette fit the tone, culture, brand and data literacy of the audience?"),
    ("TYP-M1", "Typography and labeling", "dashboard", "Are one or two sans-serif fonts used, with a clear size hierarchy (titles 24pt+, axes 14-18pt, body 10-12pt)? Check the dashboard theme."),
    ("STY-M2", "Storytelling", "page", "Can a reader state this page's hook, insight and impact in one sentence each? Is the key message seen first?"),
    ("LAY-M1", "Layout", "page", "Does the rendered page show consistent gutters and left-aligned titles and numbers?"),
    ("INT-M1", "Interactivity", "page with filters", "Does the main message stay visible whatever the filters are set to, and is it obvious how to get back to the default view?"),
    ("COL-M2", "Color", "chart with color", "Is meaning carried by more than color? Check the charts in a color-blind simulator (Color Oracle, Coblis)."),
    ("TYP-M2", "Typography and labeling", "chart with a legend", "Is the legend placed near the data, or would direct labels work better here? Are only outliers and key points labeled, with detail left to tooltips?"),
    ("AXS-M1", "Axes and gridlines", "chart with axes", "Are axis labels short (1M not 1,000,000), gridlines light and few, and number formats compact?"),
    ("ACC-M1", "Accessibility", "image", "Is each image decorative (a logo)? If one carries information, state that information in nearby text."),
]
MANUAL_NAME = {"STY-M1": "Audience and format", "COL-M1": "Palette fit", "TYP-M1": "Fonts and sizes",
               "STY-M2": "Takeaway first", "LAY-M1": "Spacing and alignment", "INT-M1": "Filters keep the message",
               "ACC-M1": "Images", "COL-M2": "Color-blind safety", "TYP-M2": "Legends and labels", "AXS-M1": "Axes and gridlines"}
GROUP = {"dashboard": "Whole dashboard", "page": "This page", "page with filters": "This page", "image": "This page",
         "chart with color": "Charts on this page", "chart with a legend": "Charts on this page", "chart with axes": "Charts on this page"}
SEV_ORDER = {"High": 0, "Medium": 1, "Low": 2}
SEV_PTS = {"High": 10, "Medium": 4, "Low": 1}


# ---------- helpers ----------
def rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lum(c):
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_white(c):
    return 1.05 / (lum(c) + 0.05)


def hls(c):
    h, l, s = colorsys.rgb_to_hls(*c)
    return h * 360, l, s


def walk(o, path=""):
    yield path, o
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")


def is_title_case(t):
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’-]*", t)]
    sig = [w for i, w in enumerate(words) if i == 0 or w.lower() not in SMALL]
    return len(sig) >= 2 and all(w[0].isupper() for w in sig)


def num(v, default=0):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else default


def as_dict(v):
    return v if isinstance(v, dict) else {}


def as_list(v):
    return v if isinstance(v, list) else []


def looks_raw(s):
    """True for code-style labels (snake_case, camelCase, backticks, aggregate expressions such as sum(amount))."""
    return bool(RAW_A.search(s) or AGG_FUNC.search(s))


KIND = {"bar": "bar chart", "line": "line chart", "area": "area chart", "pie": "pie chart", "scatter": "scatter plot",
        "combo": "combo chart", "counter": "counter", "table": "table", "pivot": "pivot table", "heatmap": "heatmap",
        "histogram": "histogram", "box": "box plot", "funnel": "funnel chart", "sankey": "sankey diagram",
        "choropleth-map": "map", "symbol-map": "map", "point-map": "map", "custom-vega-viz": "custom chart",
        "text": "text box", "image": "image", "filter-single-select": "single-select filter",
        "filter-multi-select": "multi-select filter", "filter-date-range-picker": "date range filter",
        "filter-date-picker": "date filter", "filter-text-entry": "text filter", "range-slider": "range filter"}
IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\b[^>]*>", re.I)
PERIOD = re.compile(r"\b(?:day|daily|week|weekly|month|monthly|quarter|quarterly|year|yearly|annual|annually|ytd|mtd|qtd|wtd|"
                    r"fy\d*|q[1-4]|h[12]|(?:19|20)\d\d|today|yesterday|last|past|since|to date|current|this|rolling|"
                    r"trailing|ttm|lifetime|all[- ]time|\d+\s*(?:days?|weeks?|months?|years?))\b", re.I)
ODD_FONT = re.compile(r"times|georgia|garamond|palatino|baskerville|comic|papyrus|courier|mono|brush|script|cursive|fantasy|impact|lobster", re.I)


def kind_of(wtype):
    return KIND.get(wtype) or ("filter" if wtype.startswith("filter") else wtype.replace("-", " ") + " widget")


def plain(v):
    """Display text of a title or description (a string, or {"value": ...}) without markdown or HTML markup."""
    if isinstance(v, dict):
        v = v.get("value", v.get("text"))
    if isinstance(v, list):
        v = " ".join(x for x in v if isinstance(x, str))
    if not isinstance(v, str):
        return ""
    v = IMG.sub(" ", v)
    v = re.sub(r"<[^>]+>", " ", v)
    v = re.sub(r"^\s*(?:#+|[-*]|\d+\.)\s+", "", v, flags=re.M)
    v = v.replace("**", "").replace("__", "")
    return re.sub(r"\s+", " ", v).strip()


def short(t, n=50):
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


class Widget:
    def __init__(self, pi, item, idx):
        self.item, self.idx = as_dict(item), idx
        self.w = as_dict(self.item.get("widget"))
        self.pos = as_dict(self.item.get("position"))
        self.spec = as_dict(self.w.get("spec"))
        self.is_text = "multilineTextboxSpec" in self.w
        self.lines = [l for l in as_list(as_dict(self.w.get("multilineTextboxSpec")).get("lines")) if isinstance(l, str)]
        self.text = "".join(self.lines)
        # an image widget, or a text box that holds nothing but images, is an image: never a chart
        self.is_image = "imageSpec" in self.w or (self.is_text and bool(IMG.search(self.text)) and not plain(self.text))
        wt = self.spec.get("widgetType")
        self.wtype = "image" if self.is_image else "text" if self.is_text else (wt if isinstance(wt, str) and wt else "unknown")
        self.is_filter = self.wtype.startswith("filter")
        self.is_counter = self.wtype == "counter"
        self.is_viz = not (self.is_text or self.is_image or self.is_filter or self.is_counter)
        fr = as_dict(self.spec.get("frame"))
        t = plain(fr.get("title"))
        self.title = t if fr.get("showTitle", bool(t)) else ""
        if not self.title and self.wtype == "custom-vega-viz":      # a custom chart may carry its title in the Vega spec
            js = self.spec.get("jsonSpec")
            try:
                js = json.loads(js) if isinstance(js, str) else js
            except ValueError:
                js = None
            self.title = plain(as_dict(js).get("title"))
        self.desc = plain(fr.get("description")) if fr.get("showDescription") else ""
        self.heading = ""                                            # text directly above, set by widgets_of
        self.uses_color = False
        self.name = str(self.w.get("name", f"widget{idx}"))
        self.base = f"pages[{pi}].layout[{idx}].widget"

    @property
    def snippet(self):
        for l in self.text.splitlines():
            t = plain(l)
            if t:
                return short(t)
        return ""

    @property
    def label(self):
        """Where to find the widget, in the words a dashboard user would use."""
        if self.is_text and not self.is_image:
            return f"Text box '{self.snippet}'" if self.snippet else "Empty text box"
        if self.title:
            return f"'{short(self.title)}' ({kind_of(self.wtype)})"
        return (f"Untitled {kind_of(self.wtype)}" + (f" under '{short(self.heading)}'" if self.heading else "")
                + f" at column {int(self.x()) + 1}, row {int(self.y()) + 1}")

    def x(self): return num(self.pos.get("x"))
    def y(self): return num(self.pos.get("y"))
    def wd(self): return num(self.pos.get("width"))
    def ht(self): return num(self.pos.get("height"))


def widgets_of(pi, page):
    ws = [Widget(pi, it, i) for i, it in enumerate(as_list(as_dict(page).get("layout")))
          if isinstance(it, dict) and isinstance(it.get("widget"), dict)]
    for w in ws:
        if not (w.is_text or w.is_image):
            above = [t for t in ws if t.is_text and not t.is_image and t.y() + t.ht() == w.y()
                     and t.x() < w.x() + w.wd() and w.x() < t.x() + t.wd()]
            if above:
                w.heading = above[0].snippet
    return ws


class Reviewer:
    def __init__(self, file):
        self.file, self.rows, self.manual = file, [], []

    def add(self, rule, sev, where, widget, obs, rec, path=""):
        cat, gl = GUIDE[rule]
        self.rows.append(dict(file=self.file, page=where, widget=widget, category=cat, rule=rule, severity=sev,
                              observation=obs, recommendation=rec, guideline=gl, path=path))

    def error(self, obs, rec="Fix the file so it can be reviewed."):
        self.rows.append(dict(file=self.file, page="", widget="", category="Review error", rule="ERR-01", severity="High",
                              observation=obs, recommendation=rec, guideline="", path=""))

    def ask(self, scope, page, widget, path):
        for rule, cat, sc, chk in MANUAL:
            if sc == scope:
                self.manual.append(dict(file=self.file, page=page, widget=widget, rule=rule, category=cat, check=chk, path=path,
                                        group=GROUP[sc]))

    # ---------- checks ----------
    def review(self, d):
        if not isinstance(d, dict):
            self.error(f"Unexpected structure: the file root is a {type(d).__name__}, not an object.")
            self.ask("dashboard", "All pages", "", "")
            return
        pages = as_list(d.get("pages"))
        all_titles, color_map, hexes, fonts = [], defaultdict(lambda: defaultdict(set)), defaultdict(set), defaultdict(set)
        self.ask("dashboard", "All pages", "", "")
        self.page_order = []
        for pi, p in enumerate(pages):
            p = as_dict(p)
            pname = str(p.get("displayName") or p.get("name") or f"page{pi}")
            self.page_order.append(pname)
            if p.get("pageType", "PAGE_TYPE_CANVAS") != "PAGE_TYPE_CANVAS":
                continue
            ws = widgets_of(pi, p)
            self.page_checks(pi, p, pname, ws)
            for w in ws:
                self.widget_checks(pname, w, all_titles, color_map, hexes, fonts)
            self.manual_for_page(pi, pname, ws)
        self.dashboard_checks(pages, all_titles, color_map, hexes, fonts)

    def manual_for_page(self, pi, pname, ws):
        if not ws:
            return
        self.ask("page", pname, "", f"pages[{pi}]")
        flt = [w for w in ws if w.is_filter]
        if flt:
            self.ask("page with filters", pname, "; ".join(f.label for f in flt), f"pages[{pi}]")
        for w in ws:
            enc = as_dict(w.spec.get("encodings"))
            if w.is_viz and w.uses_color:
                self.ask("chart with color", pname, w.label, w.base)
            legend = as_dict(as_dict(enc.get("color")).get("legend"))
            if w.is_viz and enc.get("color") and not (legend.get("hide") is True or legend.get("show") is False):
                self.ask("chart with a legend", pname, w.label, w.base)
            if w.is_viz and ("x" in enc or "y" in enc):
                self.ask("chart with axes", pname, w.label, w.base)
            if w.is_image:
                self.ask("image", pname, w.label + (" (small; likely a logo)" if w.wd() <= 3 and w.ht() <= 3 else ""), w.base)

    def page_checks(self, pi, p, pname, ws):
        path = f"pages[{pi}]"
        if GENERIC.match(pname.strip()) or re.search(r"[a-z]_[a-z]", pname) or pname.strip().lower().startswith("page "):
            self.add("LAY-09", "Low", pname, "", f"Page name '{pname}' is generic or machine-style.",
                     "Rename to a descriptive title-case name that says what the page answers.", path + ".displayName")
        # overlap + grid
        for a in range(len(ws)):
            A = ws[a]
            if A.x() + A.wd() > GRID:
                self.add("LAY-02", "Medium", pname, A.label, f"Widget runs to column {A.x() + A.wd()} on a {GRID}-column grid.",
                         "Resize or move the widget so it stays inside the grid.", A.base)
            for b in range(a + 1, len(ws)):
                B = ws[b]
                if A.x() < B.x() + B.wd() and B.x() < A.x() + A.wd() and A.y() < B.y() + B.ht() and B.y() < A.y() + A.ht():
                    self.add("LAY-01", "High", pname, A.label, f"Overlaps '{B.label}'.",
                             "Move one widget so each element has its own space (group related items, separate unrelated ones).", A.base)
        # heights: only flag a shorter widget when nothing is stacked directly beneath it
        rows = defaultdict(list)
        for w in ws:
            if not w.is_image:                                   # a logo beside a header is not a card in a row
                rows[w.y()].append(w)
        for y, rw in sorted(rows.items()):
            hs = {w.ht() for w in rw}
            if len(rw) > 1 and len(hs) > 1:
                def stacked(a):
                    return any(c is not a and c.y() == a.y() + a.ht() and c.x() < a.x() + a.wd() and a.x() < c.x() + c.wd() for c in ws)
                tallest = max(hs)
                if any(w.ht() < tallest and not stacked(w) for w in rw):
                    self.add("LAY-03", "Medium", pname, ", ".join(w.label for w in rw),
                             f"Widgets starting at row {y} have different heights {sorted(hs)}.",
                             "Use the same height for widgets in a row so cards align and the row reads as one band.", f"pages[{pi}].layout")
        # empty grid columns, measured on the full widget rectangles (not just rows that start at the same y)
        occ = defaultdict(set)
        for w in ws:
            c0, c1 = int(max(0, w.x())), int(min(GRID, w.x() + w.wd()))
            for r in range(int(max(0, w.y())), int(min(10000, w.y() + w.ht()))):
                occ[r].update(range(c0, c1))
        bands, cur = [], None
        for r in sorted(occ):
            cols = frozenset(occ[r])
            if len(cols) == GRID:
                cur = None
                continue
            if cur and cur["cols"] == cols and cur["end"] == r - 1:
                cur["end"] = r
            else:
                cur = {"cols": cols, "start": r, "end": r}
                bands.append(cur)
        for b in bands:
            inside = [w for w in ws if w.y() < b["end"] + 1 and w.y() + w.ht() > b["start"]]
            if inside and not all(w.is_filter or w.is_image for w in inside):
                empty = sorted(set(range(GRID)) - b["cols"])
                self.add("LAY-04", "Low", pname, ", ".join(w.label for w in inside),
                         f"Rows {b['start']}-{b['end']} leave grid column(s) {[c + 1 for c in empty]} empty ({len(b['cols'])} of {GRID} columns used).",
                         "Widen the widgets or rebalance the row so rows fill the grid evenly.", f"pages[{pi}].layout")
        # density
        viz = [w for w in ws if w.is_viz or w.is_counter]
        if len(viz) > 8:
            self.add("LAY-05", "High" if len(viz) > 12 else "Medium", pname, "", f"{len(viz)} visualizations on one page.",
                     "Split into pages or sections of about 4-8 visuals, grouped logically with clear spacing.", path)
        # key metrics first
        ctr = [w for w in ws if w.is_counter]
        charts = [w for w in ws if w.is_viz]
        if ctr and charts and min(c.y() for c in ctr) > min(c.y() for c in charts):
            self.add("LAY-06", "Medium", pname, "", "KPI counters sit below the charts.",
                     "Move headline metrics to the top row; they set up the story the charts then explain.", path)
        if len(ctr) >= 3 and len({(c.wd(), c.ht()) for c in ctr}) == 1:
            self.add("LAY-06", "Low", pname, ", ".join(c.label for c in ctr), "All KPI counters have identical size, so none leads.",
                     "Give the most important KPI more space and a larger tile; keep supporting KPIs aligned but less prominent.", path)
        # filters
        flt = [w for w in ws if w.is_filter]
        content = [w for w in ws if not w.is_filter]
        if flt and content and min(f.y() for f in flt) > min(c.y() for c in content):
            self.add("LAY-07", "Low", pname, ", ".join(f.label for f in flt), "Filters are placed below content.",
                     "Group filters in a single band at the top of the page.", path)
        # small widgets
        for w in charts:
            if w.wd() < 3 or w.ht() < 4:
                self.add("LAY-08", "Low", pname, w.label, f"Widget is only {w.wd()}x{w.ht()} grid units.",
                         "Give charts room to breathe: at least 3 columns wide and 4 rows high.", w.base)
        # annotations
        texts = [w for w in ws if w.is_text and not w.is_image]
        if len(charts) + len(ctr) >= 3 and not texts:
            self.add("ANN-01", "Low", pname, "", "No text widget gives context or points to the main insight.",
                     "Add a short headline or one callout naming the key takeaway (one sentence).", path)
        if len(texts) > 3:
            self.add("ANN-02", "Low", pname, "; ".join(t.label for t in texts), f"{len(texts)} text boxes on one page.",
                     "Keep to 1-3 annotations that point to the main insight; move secondary detail to chart descriptions or tooltips, or to a detail page.", path)
        if charts and texts and min(t.y() for t in texts) > min(c.y() for c in charts):
            first = min(charts, key=lambda c: (c.y(), c.x()))
            self.add("STY-02", "Low", pname, first.label, "The page opens with a chart; no headline or takeaway text comes before it.",
                     "Start the page with a one-line headline that states the main takeaway, so readers know what to look for before the charts.", path)
        if len(flt) > 3:
            self.add("INT-01", "Medium" if len(flt) > 5 else "Low", pname, "; ".join(f.label for f in flt),
                     f"{len(flt)} filters on one page.",
                     "Keep the filters this audience actually uses (about 3 per page); move the rest to a detail page or combine related ones.", path)

    def widget_checks(self, pname, w, titles, color_map, hexes, fonts):
        if w.is_text or w.is_image:
            self.text_checks(pname, w, fonts)
            return
        if w.is_filter:
            self.filter_checks(pname, w)
            return
        if not w.title and w.heading:
            self.add("TYP-01", "Low", pname, w.label,
                     f"The chart has no title of its own; the text above it ('{short(w.heading)}') acts as one.",
                     "Give the chart its own short title (it can repeat the heading's message) so it stays labeled when viewed full screen, exported or moved.",
                     w.base + ".spec.frame")
        elif not w.title:
            self.add("TYP-01", "Medium", pname, w.label, "The chart has no visible title and no heading above it.",
                     "Add a descriptive title that says what is measured and for whom, in title case.", w.base + ".spec.frame")
        if w.is_viz and not w.desc:
            self.add("ACC-01", "Low", pname, w.label, "No description is shown for this chart.",
                     "Add a one-sentence description of what the chart shows and its takeaway, and turn on 'Show description'; it helps screen-reader users and anyone viewing the chart out of context.",
                     w.base + ".spec.frame")
        if w.is_counter and w.title and not PERIOD.search(w.title + " " + w.desc):
            self.add("STY-01", "Low", pname, w.label, f"KPI '{short(w.title)}' does not say which period it covers.",
                     "Add the period, and the unit if it is not obvious, for example 'Total Cost, Last 30 Days ($)' or a description such as 'Year to date'.",
                     w.base + ".spec.frame.title")
        if w.title:
            titles.append((pname, w, w.title))
            self.title_checks(pname, w, w.title)
        self.label_checks(pname, w)
        self.color_checks(pname, w, color_map, hexes)

    def title_checks(self, pname, w, t):
        probs = []
        if GENERIC.match(t): probs.append("placeholder text")
        if re.search(r"[A-Za-z]_[A-Za-z]", t) or (re.search(r"[a-z][A-Z]", t.replace(" ", "")) and " " not in t): probs.append("code-style name")
        letters = re.sub(r"[^A-Za-z]", "", t)
        if len(letters) > 4 and t == t.upper(): probs.append("ALL CAPS")
        ab = sorted({x for x in re.findall(r"[A-Za-z]+", t.lower()) if x in ABBREV})
        if ab: probs.append("abbreviations (" + ", ".join(ab) + ")")
        if len(t) > 60: probs.append(f"{len(t)} characters")
        if probs:
            self.add("TYP-02", "Medium", pname, w.label, f"Title '{t}': " + "; ".join(probs) + ".",
                     "Spell it out, use title case, and make it descriptive but under about 60 characters.", w.base + ".spec.frame.title")

    def label_checks(self, pname, w):
        enc = as_dict(w.spec.get("encodings"))
        bad = []
        for ch, e in enc.items():
            for it in (e if isinstance(e, list) else [e]):
                if not isinstance(it, dict):
                    continue
                dn = it.get("displayName") or as_dict(it.get("axis")).get("title") or ""
                fn = it.get("fieldName") or ""
                dn, fn = dn if isinstance(dn, str) else "", fn if isinstance(fn, str) else ""
                if dn and looks_raw(dn):
                    bad.append(f"{ch}: '{dn}'")
                elif not dn and fn and looks_raw(fn) and w.wtype != "table":
                    bad.append(f"{ch}: field '{fn}' has no display name")
        if bad:
            self.add("TYP-04", "Medium", pname, w.label, "Raw or auto-generated labels: " + "; ".join(bad[:6]) + ".",
                     "Set readable display names (for example 'Order Date', 'Total Revenue ($M)'); hide the axis title when the chart title already says it.",
                     w.base + ".spec.encodings")
        if w.wtype == "table":
            cols = as_list(enc.get("columns"))
            if len(cols) > 10:
                self.add("TYP-06", "Medium", pname, w.label, f"Table has {len(cols)} columns.",
                         "Trim to the columns the audience needs; move the rest to a detail page or tooltip.", w.base + ".spec.encodings.columns")

    def filter_checks(self, pname, w):
        if not w.title:
            self.add("INT-02", "Medium", pname, w.label, "The filter has no visible label.",
                     "Add a short label that says what the filter controls, in the audience's words (for example 'Region', not 'region_cd').",
                     w.base + ".spec.frame")
        preset = as_dict(as_dict(w.spec.get("selection")).get("defaultSelection"))
        if preset and w.wtype != "filter-single-select":           # a single-select filter needs a starting value
            vals = [str(as_dict(v).get("value")) for _, v in walk(preset) if isinstance(v, dict) and "value" in v and not isinstance(v.get("value"), (dict, list))]
            self.add("INT-03", "Low", pname, w.label, "The filter opens with a preset selection" + (f" ({', '.join(vals[:3])})" if vals else "") + ".",
                     "Open with no preset selection, or say in the page headline that the view is pre-filtered, so readers are not misled by a partial picture.",
                     w.base + ".spec.selection")

    def text_checks(self, pname, w, fonts):
        lines, txt = w.lines, w.text
        for m in re.finditer(r"!\[([^\]]*)\]\(", txt):
            if not m.group(1).strip():
                self.add("ACC-02", "Low", pname, w.label, "An image in this text box has no alternative text.",
                         "Add alternative text inside the brackets, ![like this](...), describing what the image shows; leave it empty only for decorative images.",
                         w.base + ".multilineTextboxSpec")
                break
        for m in re.finditer(r"<img\b[^>]*>", txt, re.I):
            if not re.search(r"\balt\s*=\s*[\"'][^\"']+", m.group(0), re.I):
                self.add("ACC-02", "Low", pname, w.label, "An HTML image in this text box has no alt text.",
                         "Add alt=\"...\" describing what the image shows; leave it empty only for decorative images.", w.base + ".multilineTextboxSpec")
                break
        for f in re.findall(r"font-family\s*:\s*([^;\"'>]+)", txt, re.I):
            fonts[f.split(",")[0].strip().strip("'\"")].add(f"{pname}: {w.label}")
        small = sorted({float(x) for x in re.findall(r"font-size\s*:\s*([\d.]+)px", txt, re.I) if float(x) < 12})
        if small:
            self.add("TYP-07", "Low", pname, w.label, f"Text set at {', '.join(f'{x:g}px' for x in small)}, below a comfortable reading size.",
                     "Use at least 12px (about 10-12pt) for body text and larger sizes for headings.", w.base + ".multilineTextboxSpec")
        if w.is_image:
            return
        if len(txt) > 500 or len(lines) > 8:
            self.add("TYP-05", "Low", pname, w.label, f"Text widget holds {len(txt)} characters over {len(lines)} lines.",
                     "Cut to a headline plus one sentence; put detail in a description or tooltip.", w.base + ".multilineTextboxSpec")
        shouting = [l for l in lines if len(re.sub(r"[^A-Za-z]", "", l)) > 12 and l == l.upper()]
        if shouting:
            self.add("TYP-05", "Low", pname, w.label, "ALL CAPS lines in text widget.",
                     "Use sentence or title case; all caps slows reading and feels aggressive.", w.base + ".multilineTextboxSpec")
        if sum(1 for l in lines if re.match(r"^#\s", l)) > 1:
            self.add("TYP-05", "Low", pname, w.label, "More than one top-level heading in one text widget.",
                     "Use one H1, then H2/H3 for sub-levels, to preserve a clear hierarchy.", w.base + ".multilineTextboxSpec")

    def color_checks(self, pname, w, color_map, hexes):
        found, maps = [], []
        for path, v in walk(w.w):
            if isinstance(v, str) and HEX.match(v):
                found.append(v.lower())
            if isinstance(v, dict) and "value" in v and "color" in v:
                c = v["color"]
                if isinstance(c, str):
                    key = c.lower()
                elif isinstance(c, dict) and "themeColorType" in c:
                    key = f"theme color {c.get('position', '?')}"
                else:
                    key = json.dumps(c, sort_keys=True)
                maps.append((str(v["value"]), key))
                color_map[str(v["value"])][key].add(f"{pname}: {w.label}")
            # a named rainbow-style scheme (only on scheme keys, never on titles or labels)
            if isinstance(v, str) and re.split(r"[.\[]", path)[-1] in ("scheme", "colorScheme") and re.search(r"rainbow|jet|spectral|turbo", v, re.I):
                self.add("COL-02", "Medium", pname, w.label, f"Color scheme '{v}' is rainbow-style.",
                         "Switch to a sequential (one hue) or diverging (two hues around a neutral midpoint) palette.", w.base + "." + path)
            # a continuous ramp that walks across many hue families (categorical palettes are not ramps)
            if isinstance(v, dict) and path.split(".")[-1] == "colorRamp":
                ramp = [rgb(s) for _, s in walk(v) if isinstance(s, str) and HEX.match(s)]
                ramp = [c for c in ramp if hls(c)[2] > 0.25]
                fams = {int(hls(c)[0] // 60) for c in ramp}
                if len(ramp) >= 4 and len(fams) >= 4:
                    self.add("COL-02", "Medium", pname, w.label, f"Color ramp spans {len(fams)} hue families.",
                             "Use a single-hue sequential ramp or a diverging ramp with a neutral midpoint.", w.base + "." + path)
        distinct = sorted(set(found))
        for c in distinct:
            hexes[c].add(f"{pname}: {w.label}")
        w.uses_color = bool(distinct or maps or as_dict(w.spec.get("encodings")).get("color"))
        if len(distinct) > 8 or len(maps) > 8:
            self.add("COL-01" if len(distinct) > 8 else "COL-06", "Medium", pname, w.label,
                     f"{max(len(distinct), len(maps))} distinct colors/categories in one widget.",
                     "Reserve bold color for what matters; group related categories under one color and gray out the rest (about 6-8 groups at most).", w.base)
        rg = [rgb(c) for c in distinct if len(c) in (4, 7)]
        hl = [hls(c) for c in rg]
        reds = [c for c, (h, l, s) in zip(rg, hl) if (h <= 20 or h >= 340) and s > 0.35 and 0.25 < l < 0.75]
        greens = [c for c, (h, l, s) in zip(rg, hl) if 80 <= h <= 160 and s > 0.3 and 0.2 < l < 0.75]
        if reds and greens:
            self.add("COL-03", "High", pname, w.label, "Saturated red and green used together.",
                     "Replace with a color-blind-safe pair (for example orange and blue) and add labels, icons or line style as a second cue.", w.base)
        faint = [c for c in distinct if len(c) == 7 and contrast_white(rgb(c)) < 2 and hls(rgb(c))[2] > 0.2]
        if faint:
            self.add("COL-04", "Low", pname, w.label, f"Very light saturated marks on white: {', '.join(faint[:3])}.",
                     "Darken so key marks keep at least 3:1 contrast with the background; keep very light tones for context only.", w.base)
        sat = [c for c, (h, l, s) in zip(rg, hl) if s > 0.35]
        for i in range(len(sat)):
            for j in range(i + 1, len(sat)):
                if sum((a - b) ** 2 for a, b in zip(sat[i], sat[j])) ** .5 < 0.12:
                    self.add("COL-04", "Medium", pname, w.label, "Two saturated colors in one widget are nearly identical.",
                             "Pick colors with clearly different lightness or hue, or merge the categories.", w.base)
                    return

    def dashboard_checks(self, pages, titles, color_map, hexes, fonts):
        """Findings that span pages name every page and widget involved, so each one can be found."""
        def pages_of(places):                                   # in dashboard order, so reports are repeatable
            names = {x.split(": ", 1)[0] for x in places}
            return ", ".join(sorted(names, key=lambda n: (self.page_order.index(n) if n in self.page_order else len(self.page_order), n)))

        def listing(places, n=8, keep_order=False):
            places = list(places) if keep_order else sorted(places)
            return "; ".join(places[:n]) + (f"; and {len(places) - n} more" if len(places) > n else "")

        if len(hexes) > 12:
            per = defaultdict(set)
            for c, places in hexes.items():
                for x in places:
                    per[x].add(c)
            busiest = sorted(per.items(), key=lambda kv: (-len(kv[1]), kv[0]))
            self.add("COL-01", "Medium", pages_of(per), listing([f"{x} ({len(cs)} colors)" for x, cs in busiest], keep_order=True),
                     f"{len(hexes)} distinct colors across the dashboard; the widgets listed use the most.",
                     "Define one small palette (about 6 colors including grays) and reuse it everywhere, starting with the widgets listed.", "")
        for val, cmap in color_map.items():
            if len(cmap) > 1:
                places = [f"{x} = {c}" for c, xs in cmap.items() for x in xs]
                self.add("COL-05", "Medium", pages_of(places), listing(places), f"'{val}' is shown in {len(cmap)} different colors.",
                         f"Give '{val}' one color and use it in every chart listed.", "")
        tc = [(f"{pn}: '{short(t)}'", is_title_case(t)) for pn, _, t in titles if len(t.split()) > 1]
        flags = [f for _, f in tc]
        if flags and 0 < sum(flags) < len(flags) and min(sum(flags), len(flags) - sum(flags)) / len(flags) >= 0.25:
            minority = sum(flags) < len(flags) - sum(flags)          # list the less common style: those are the ones to change
            odd = [x for x, f in tc if f == minority]
            self.add("TYP-03", "Low", pages_of(odd), listing(odd),
                     f"Titles mix title case ({sum(flags)}) and sentence case ({len(flags) - sum(flags)}); the titles listed use the less common "
                     + ("title case." if minority else "sentence case."),
                     "Pick one convention (title case is recommended) and apply it to every chart title.", "")
        odd = {f: xs for f, xs in fonts.items() if ODD_FONT.search(f)}
        if len(fonts) > 2 or odd:
            places = [f"{x} uses {f}" for f, xs in fonts.items() for x in xs]
            self.add("TYP-07", "Low", pages_of(places), listing(places),
                     f"Text boxes set {len(fonts)} font families ({', '.join(sorted(fonts))})"
                     + (f"; {', '.join(sorted(odd))} is not a clean sans-serif" if odd else "") + ".",
                     "Use one or two sans-serif fonts across the dashboard, ideally the theme font, and remove inline font overrides.", "")
        if pages:
            first = widgets_of(0, pages[0])
            if not any(w.is_text and not w.is_image for w in first):
                self.add("ANN-03", "Low", str(as_dict(pages[0]).get("displayName", "page 1")), "", "First page has no title or overview text.",
                         "Open with a short title/overview text widget that frames the question the dashboard answers.", "pages[0]")


def find_files(root):
    r = Path(root)
    if r.is_file():
        return [r]
    return sorted(r.rglob("*.lvdash.json"))


def report_name(path, files, label, ext):
    """Meaningful default file name: '<dashboards> - <label> - <date>.<ext>', numbered ' (2)' if it exists.

    One file: its name ('sales - ...'). Several: the words their names share ('Finance Dashboards - ...'),
    else the bundle folder ('my_bundle Dashboards - ...')."""
    stems = [f.name[:-len(".lvdash.json")] if f.name.endswith(".lvdash.json") else f.stem for f in files]
    if len(stems) == 1:
        base = stems[0]
    else:
        words = [[w for w in re.split(r"[\s_\-]+", s) if w] for s in stems]
        common = []
        for group in zip(*words):
            if len({w.lower() for w in group}) > 1:
                break
            common.append(group[0])
        if not common:
            folder = Path(path).resolve()
            folder = folder.parent if folder.name.lower() in ("dashboards", "src", "resources") else folder
            common = [folder.name or "Dashboards"]
        base = " ".join(common)
        if not base.lower().endswith(("dashboard", "dashboards")):
            base += " Dashboards"
    base = re.sub(r'[\\/:*?"<>|]+', "-", base).strip(" .-") or "Dashboards"
    name, n = f"{base} - {label} - {datetime.date.today().isoformat()}", 1
    while Path(f"{name}{f' ({n})' if n > 1 else ''}.{ext}").exists():    # never overwrite an earlier report
        n += 1
    return f"{name}{f' ({n})' if n > 1 else ''}.{ext}"


def put(ws, row):
    """Append a row, removing characters Excel cannot store and keeping text that starts with '=' as text."""
    ws.append([ILLEGAL_CHARACTERS_RE.sub("", v) if isinstance(v, str) else v for v in row])
    for c in ws[ws.max_row]:
        if isinstance(c.value, str) and c.value[:1] in ("=", "+", "-", "@"):
            c.data_type = "s"


CATEGORIES = ["Color", "Typography and labeling", "Layout", "Annotations", "Accessibility", "Interactivity", "Storytelling"]
README = [
    ("About this report", "Suggestions to help you improve these dashboards. They are not errors and nothing has been changed: "
                          "the dashboard files were only read. Review each suggestion, decide whether it fits your audience "
                          "and purpose, and act on the ones that do."),
    ("Summary", "One row per dashboard: a rough score (100 minus 10 per High, 4 per Medium and 1 per Low suggestion) and the "
                "number of suggestions by priority and category. Use it to decide where to start, not as a grade."),
    ("Suggestions", "One row per suggestion: where it is (page and widget), what was found, the suggested change and the "
                    "guideline behind it. Untitled widgets are described by their type, the text above them and their "
                    "position on the page grid (column 1-12 from the left, row from the top). The JSON path is for whoever "
                    "edits the dashboard file."),
    ("Manual review", "Checks a script cannot make: one row for the whole dashboard, then for each page one row about the "
                      "page and one about its charts. Each row lists its checks once, numbered, with the charts, filters or "
                      "images each one applies to. Look at the rendered dashboard and record Pass, Fail or N/A, with a note "
                      "naming any chart that fails."),
    ("Rules", "Every rule, its guideline in one sentence, and whether it is checked automatically."),
    ("Priority", "High: likely to mislead or exclude readers (overlaps, red-green pairs, very crowded pages). "
                 "Medium: weakens clarity (missing titles, raw labels, inconsistent colors). Low: polish."),
    ("Status", "Every suggestion starts as 'To consider'. Change it to Accepted, Done or Not applicable as you work "
               "through the list, and add a note when you decide a suggestion does not apply."),
]


def condense(manual):
    """One row per dashboard, and per page one row for the page and one for its charts. Each row lists its checks
    once, numbered, with the widgets each applies to, instead of repeating a check for every chart."""
    groups, order = defaultdict(lambda: defaultdict(list)), []
    for m in manual:
        key = (m["file"], m["page"], m["group"])
        if key not in groups:
            order.append(key)
        groups[key][m["rule"]].append(m["widget"])
    rank = {r: i for i, (r, *_) in enumerate(MANUAL)}
    check = {r: c for r, _, _, c in MANUAL}
    rows = []
    for key in order:
        rules = sorted(groups[key], key=rank.get)
        lists = {r: [w for w in dict.fromkeys(groups[key][r]) if w] for r in rules}
        charts = key[2] == "Charts on this page"
        union = list(dict.fromkeys(w for r in rules for w in lists[r])) if charts else []
        items = [f"Charts: {'; '.join(union)}"] if union else []          # name the charts once, at the top
        for n, rule in enumerate(rules, 1):
            where = lists[rule]
            if charts:
                tail = "" if set(where) == set(union) else "\n   Only: " + "; ".join(where)
            else:
                label = "Filters" if rule == "INT-M1" else "Images" if rule == "ACC-M1" else "Charts"
                tail = f"\n   {label}: " + "; ".join(where) if where else ""
            items.append(f"{n}. {MANUAL_NAME[rule]} ({rule}): {check[rule]}{tail}")
        rows.append(dict(file=key[0], page=key[1], scope=key[2], checks="\n".join(items),
                         rules=", ".join(sorted(groups[key], key=rank.get))))
    return rows


def write_xlsx(results, files, out):
    wb = Workbook()
    hdr_fill = PatternFill("solid", fgColor="002244")
    hdr_font = Font(bold=True, color="FFFFFF")
    sev_fill = {"High": "F8D7C4", "Medium": "FFF2CC", "Low": "EAF7FB"}

    def style(ws, widths):
        for c in ws[1]:
            c.fill, c.font, c.alignment = hdr_fill, hdr_font, Alignment(vertical="center", wrap_text=True)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(vertical="top", wrap_text=True)

    ws = wb.active
    ws.title = "Read me"
    ws.append(["Dashboard design review", "These are suggestions for you to act on, not errors."])
    for row in README:
        put(ws, list(row))
    style(ws, [22, 110])
    for c in ws["A"][1:]:
        c.font = Font(bold=True, color="002244")

    ws = wb.create_sheet("Summary")
    ws.append(["File", "Score (0-100)", "High", "Medium", "Low", *CATEGORIES, "Total suggestions"])
    for f in files:
        rows = results[f][0]
        sev = lambda s: sum(r["severity"] == s for r in rows)
        cat = lambda c: sum(r["category"] == c for r in rows)
        score = max(0, 100 - sum(SEV_PTS[r["severity"]] for r in rows))
        put(ws, [str(f), score, sev("High"), sev("Medium"), sev("Low"), *(cat(c) for c in CATEGORIES), len(rows)])
    style(ws, [60, 14, 8, 10, 8] + [12] * len(CATEGORIES) + [14])

    ws = wb.create_sheet("Suggestions")
    ws.append(["File", "Page", "Widget", "Category", "Rule", "Priority", "What was found", "Suggested change", "Guideline", "JSON path", "Status"])
    allrows = sorted((r for f in files for r in results[f][0]), key=lambda r: (r["file"], SEV_ORDER[r["severity"]], r["rule"]))
    for r in allrows:
        put(ws, [r["file"], r["page"], r["widget"], r["category"], r["rule"], r["severity"], r["observation"],
                 r["recommendation"], r["guideline"], r["path"], "To consider"])
        ws.cell(ws.max_row, 6).fill = PatternFill("solid", fgColor=sev_fill[r["severity"]])
    style(ws, [34, 22, 40, 20, 9, 10, 55, 70, 45, 38, 12])
    if allrows:
        ws.auto_filter.ref = ws.dimensions

    ws = wb.create_sheet("Manual review")
    ws.append(["File", "Page", "Scope", "What to check", "Rules", "Result (Pass / Fail / N/A)", "Notes"])
    for f in files:
        for m in condense(results[f][1]):
            put(ws, [m["file"], m["page"], m["scope"], m["checks"], m["rules"], "To review", ""])
    style(ws, [34, 24, 18, 110, 16, 16, 34])
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions

    ws = wb.create_sheet("Rules")
    ws.append(["Rule", "Category", "Guideline", "Automated"])
    for k, (cat, gl) in GUIDE.items():
        ws.append([k, cat, gl, "Yes"])
    for rule, cat, scope, chk in MANUAL:
        ws.append([rule, cat, chk, f"No - manual, once per {scope}"])
    style(ws, [10, 24, 80, 26])
    wb.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default="dashboards", help="dashboards directory or a single .lvdash.json")
    ap.add_argument("-o", "--output", help="report path (default: '<dashboards> - Design Review - <date>.xlsx')")
    a = ap.parse_args()
    if not Path(a.path).exists():
        sys.exit(f"Path not found: {a.path}")
    files = find_files(a.path)
    if not files:
        sys.exit(f"No *.lvdash.json files found under {a.path}")
    a.output = a.output or report_name(a.path, files, "Design Review", "xlsx")
    if not Path(a.output).resolve().parent.is_dir():
        sys.exit(f"Output folder does not exist: {Path(a.output).parent}")
    results = {}
    for f in files:
        rv = Reviewer(str(f))
        try:
            rv.review(json.loads(f.read_text(encoding="utf-8-sig")))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            rv.error(f"Invalid JSON: {e}", "Fix the JSON before review.")
        except Exception as e:                                  # one bad file must not stop the run
            rv.error(f"Could not review this file ({type(e).__name__}: {e}).")
        results[f] = (rv.rows, rv.manual)
    write_xlsx(results, files, a.output)
    total = sum(len(v[0]) for v in results.values())
    print(f"Reviewed {len(files)} file(s), {total} suggestion(s) -> {a.output}")


if __name__ == "__main__":
    main()
