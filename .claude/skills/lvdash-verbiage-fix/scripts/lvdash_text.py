#!/usr/bin/env python3
"""Find and fix user-facing wording in Databricks AI/BI (Lakeview) *.lvdash.json files.

Subcommands
  extract PATH            list every user-facing string with its JSON path (for review)
  fix PATH                deterministic fixes: spacing, US spelling, grammar, professional tone
  apply PATH edits.json   apply reviewed rewrites: [{"file","path","new"[, "old"]}, ...]

fix and apply are DRY RUNS unless --write is given: the originals are not touched. A fix dry run also writes
the full set of dashboards, fixed where needed, to dashboard_verbiage_fix/ (--copies-dir to change, --no-copies
to skip), so the result can be opened and compared before anything is replaced. Each run writes a CSV report named after the dashboards,
the run and the date (for example "Sales Dashboards - Wording Fixes (Proposed) - 2026-11-16.csv"); use --report PATH
to choose the name or --no-report to skip it. Only display text is touched: page names,
widget titles and descriptions, axis/column labels, text-widget markdown. SQL (queryLines),
field names, expressions, ids, colors and data values are never modified.
"""
import argparse, csv, datetime, json, re, sys
from pathlib import Path

# ---------------------------------------------------------------- vocabularies
ACRONYMS = {w.upper() for w in """kpi ytd mtd qtd wow yoy mom id ids url api usa uk eu usd cad gbp eur ai bi etl elt roi csat nps sla sku
b2b b2c crm erp hr pdf csv json sql dbx dab ui ux ml llm cpu gpu aws gcp ceo cfo cto coo vp fy q1 q2 q3 q4 h1 h2 ngo
ngos ebitda cogs arr mrr gdp cpi ytd tbd faq pii ip kpis rfp""".split()}
SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "per", "the", "to",
         "vs", "vs.", "via", "with", "from", "into", "than", "so", "yet", "if"}
BASE_STOP = ("the", "a", "an")

def _spell_map():
    m = {}
    for gb in ["colour", "favour", "honour", "labour", "neighbour", "flavour", "humour", "rumour", "harbour", "savour",
               "behaviour", "vapour", "endeavour", "armour", "odour", "rigour", "vigour", "parlour", "tumour", "candour"]:
        for suf in ["", "s", "ed", "ing", "ite", "ites", "able", "ful", "less", "ist", "ists", "al", "ally", "ation"]:
            m[gb + suf] = gb.replace("our", "or") + suf
    for gb in ["centre", "metre", "litre", "fibre", "theatre", "calibre", "lustre", "sabre", "spectre"]:
        us = gb[:-2] + "er"
        for suf, usuf in [("", ""), ("s", "s"), ("d", "ed")]:
            m[gb + suf] = us + usuf
    m.update({"centring": "centering", "centred": "centered"})
    stems = """organis recognis realis summaris prioritis customis standardis optimis normalis categoris visualis minimis
    maximis finalis emphasis authoris capitalis localis centralis specialis synchronis characteris harmonis apologis
    criticis memoris digitis monetis modernis mobilis formalis generalis personalis rationalis stabilis analys paralys
    catalys civilis colonis computeris crystallis equalis familiaris hospitalis immunis legalis materialis neutralis
    penalis popularis randomis revolutionis scrutinis sensitis socialis symbolis sympathis tokenis vandalis vaporis
    virtualis operationalis utilis itemis categoris prioritis tabulis econimis""".split()
    for s in stems:
        us = s[:-1] + "z"
        for suf in ["e", "ed", "es", "ing", "er", "ers", "ation", "ations", "able"]:
            if s == "emphasis" and suf in ("ation", "ations", "able", "er", "ers"):
                continue
            m[s + suf] = us + suf
    m.pop("emphasise", None); m["emphasise"] = "emphasize"
    m.update({
        "analysed": "analyzed", "analyse": "analyze", "grey": "gray", "greys": "grays", "greyed": "grayed",
        "catalogue": "catalog", "catalogues": "catalogs", "programme": "program", "programmes": "programs",
        "cheque": "check", "cheques": "checks", "tyre": "tire", "kerb": "curb", "aluminium": "aluminum",
        "defence": "defense", "offence": "offense", "licence": "license", "licences": "licenses", "practise": "practice",
        "practised": "practiced", "practising": "practicing", "enrolment": "enrollment", "enrolments": "enrollments",
        "fulfil": "fulfill", "fulfils": "fulfills", "fulfilment": "fulfillment", "skilful": "skillful",
        "judgement": "judgment", "judgements": "judgments", "ageing": "aging", "acknowledgement": "acknowledgment",
        "artefact": "artifact", "artefacts": "artifacts", "sceptical": "skeptical", "sceptic": "skeptic",
        "whilst": "while", "amongst": "among", "towards": "toward", "learnt": "learned", "spelt": "spelled",
        "burnt": "burned", "maths": "math", "mould": "mold", "plough": "plow", "cosy": "cozy", "draught": "draft",
        "storey": "story", "storeys": "stories", "sulphur": "sulfur", "jewellery": "jewelry", "manoeuvre": "maneuver",
        "pyjamas": "pajamas", "mum": "mom", "postcode": "postal code", "postcodes": "postal codes",
        "labelled": "labeled", "labelling": "labeling", "modelled": "modeled", "modelling": "modeling",
        "cancelled": "canceled", "cancelling": "canceling", "travelled": "traveled", "travelling": "traveling",
        "traveller": "traveler", "travellers": "travelers", "signalled": "signaled", "signalling": "signaling",
        "fuelled": "fueled", "levelled": "leveled", "levelling": "leveling", "totalled": "totaled", "totalling": "totaling",
        "counselled": "counseled", "channelled": "channeled", "channelling": "channeling", "tunnelled": "tunneled",
        "benefitted": "benefited", "focussed": "focused", "focussing": "focusing",
        "neighbourhood": "neighborhood", "neighbourhoods": "neighborhoods", "enquiry": "inquiry", "enquiries": "inquiries",
        "enquire": "inquire", "enquired": "inquired", "enquiring": "inquiring", "paediatric": "pediatric", "paediatrics": "pediatrics",
        "anaemia": "anemia", "anaemic": "anemic", "anaesthetic": "anesthetic", "oestrogen": "estrogen", "haemoglobin": "hemoglobin",
        "foetus": "fetus", "encyclopaedia": "encyclopedia", "aeroplane": "airplane", "diarrhoea": "diarrhea",
        "orthopaedic": "orthopedic", "leukaemia": "leukemia", "per cent": "percent", "licenced": "licensed",
        "licencing": "licensing", "chequing": "checking", "enrol": "enroll", "enrols": "enrolls", "instalment": "installment",
        "instalments": "installments", "wilful": "willful", "distil": "distill", "pretence": "pretense", "analogue": "analog",
        "somber": "somber", "sombre": "somber", "meagre": "meager", "kilometre": "kilometer", "kilometres": "kilometers",
        "centimetre": "centimeter", "centimetres": "centimeters", "millimetre": "millimeter", "millimetres": "millimeters",
        "kilolitre": "kiloliter", "millilitre": "milliliter", "millilitres": "milliliters", "metres": "meters",
        "organisational": "organizational", "organisationally": "organizationally", "judgemental": "judgmental",
        "licensee": "licensee", "grey-scale": "gray-scale", "colour-blind": "color-blind", "cheques": "checks",
    })
    for stem in ("organis", "recognis", "realis", "summaris", "prioritis", "customis", "standardis", "optimis", "normalis",
                 "categoris", "visualis", "utilis", "minimis", "maximis", "finalis", "authoris", "capitalis", "localis"):
        m[stem + "ational"] = stem[:-1] + "zational"
    m.pop("mum", None); m.pop("postcode", None); m.pop("postcodes", None)
    return m

SPELL = _spell_map()
TYPOS = {"recieve": "receive", "recieved": "received", "seperate": "separate", "seperated": "separated", "occured": "occurred",
         "occurence": "occurrence", "definately": "definitely", "accomodate": "accommodate", "wich": "which", "teh": "the",
         "adress": "address", "begining": "beginning", "beleive": "believe", "calender": "calendar", "commited": "committed",
         "consistant": "consistent", "existance": "existence", "goverment": "government", "independant": "independent",
         "neccessary": "necessary", "necesary": "necessary", "persistant": "persistent", "publically": "publicly",
         "refered": "referred", "relevent": "relevant", "succesful": "successful", "successfull": "successful",
         "tommorow": "tomorrow", "untill": "until", "wierd": "weird", "acheive": "achieve", "enviroment": "environment",
         "managment": "management", "comparision": "comparison", "alot": "a lot", "thier": "their", "becuase": "because",
         "reveune": "revenue", "revnue": "revenue", "custmer": "customer", "avarage": "average", "totla": "total",
         "performace": "performance", "dashbaord": "dashboard", "occuring": "occurring", "arguement": "argument"}
CONTR = {"don't": "do not", "doesn't": "does not", "didn't": "did not", "can't": "cannot", "won't": "will not",
         "isn't": "is not", "aren't": "are not", "wasn't": "was not", "weren't": "were not", "haven't": "have not",
         "hasn't": "has not", "hadn't": "had not", "shouldn't": "should not", "wouldn't": "would not",
         "couldn't": "could not", "it's": "it is", "that's": "that is", "there's": "there is", "here's": "here is",
         "what's": "what is", "who's": "who is", "we're": "we are", "you're": "you are", "they're": "they are",
         "i'm": "I am", "we've": "we have", "you've": "you have", "they've": "they have", "we'll": "we will",
         "you'll": "you will", "they'll": "they will", "it'll": "it will", "let's": "let us", "i've": "I have",
         "i'll": "I will", "mustn't": "must not", "needn't": "need not"}
INFORMAL = {"gonna": "going to", "wanna": "want to", "gotta": "have to", "kinda": "somewhat", "sorta": "somewhat",
            "thx": "thank you", "pls": "please", "plz": "please", "info": "information", "stats": "statistics",
            "a bit": "slightly", "w/o": "without", "w/": "with", "approx.": "approximately", "tho": "though",
            "lemme": "let me", "dunno": "do not know"}
FILLER = ["really", "very", "basically", "actually", "literally", "totally", "obviously", "simply", "honestly"]
ABBR_EXPAND = {"qtly": "Quarterly", "qty": "Quantity", "amt": "Amount", "avg": "Average", "cnt": "Count", "pct": "Percent",
               "yr": "Year", "mth": "Month", "wk": "Week", "cust": "Customer", "dept": "Department", "mgr": "Manager",
               "nbr": "Number", "tot": "Total"}
HYPE = {"awesome", "amazing", "great", "cool", "huge", "stuff", "things", "guys", "killer", "crazy", "insane", "super",
        "just", "pretty", "nice", "terrible", "horrible", "bad", "good", "big", "lots", "tons", "wow", "oops"}
AMBIGUOUS_ABBR = {"rev", "reg", "val", "cat", "grp", "desc", "num", "prod"}
STRICT_AN = {"hour", "hours", "honest", "honesty", "honor", "honors", "heir", "heirs", "honorable"}
STRICT_A = {"unique", "user", "users", "use", "used", "useful", "usual", "union", "unit", "units", "uniform", "university",
            "european", "one", "once", "utility", "usage", "unified", "universal", "url", "uri", "ui", "uuid", "unicorn"}
AN_LETTERS = set("AEFHILMNORSX")

# ---------------------------------------------------------------- protected spans
PROTECT = re.compile(r"</?[A-Za-z][^<>]*>|`[^`]*`|https?://[^\s)\]]*[^\s)\].,;:!?]|\]\([^)]*\)|\{\{[^}]*\}\}|:\w+(?=[\s,)]|$)|[\w.+-]+@[\w-]+\.[\w.]+")
EMOJI = re.compile("[\U0001F000-\U0001FAFF️]")
LETTER = re.compile(r"[^\W\d_]")
ABBR_NOCAP = {"e.g", "i.e", "vs", "etc", "inc", "ltd", "co", "corp", "dr", "mr", "mrs", "ms", "no", "nos", "fig", "approx",
              "est", "st", "jr", "sr", "vol", "avg", "dept", "cf", "al", "ca", "ave", "eg", "ie", "a.m", "p.m"}
FUNC_NAME = re.compile(r"^[A-Za-z_][\w.]*\([^)]*\)$")
AGG_TITLE = re.compile(r"[A-Za-z0-9]_[A-Za-z0-9]")


def case_like(src, repl):
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


class Ctx:
    def __init__(self, keep=(), tone=True, titlecase=True):
        self.keep = {k.lower() for k in keep}
        self.tone, self.titlecase = tone, titlecase


_PAT_CACHE = {}


def word_sub(text, table, ctx, rule, fired, flags=re.I):
    pat = _PAT_CACHE.get(id(table))
    if pat is None:
        pat = _PAT_CACHE[id(table)] = re.compile(
            r"(?<![\w'\u2019])(" + "|".join(sorted(map(re.escape, table), key=len, reverse=True)) + r")(?![\w'\u2019])", flags)

    def rep(m):
        w = m.group(1)
        if w.lower() in ctx.keep:
            return w
        fired.add(rule)
        return case_like(w, table[w.lower()])
    return pat.sub(rep, text)


# ---------------------------------------------------------------- transforms
def cap_sentences(s):
    """Capitalize the first letter after a sentence end, but not after abbreviations (e.g., U.S., vs.) or inside ellipses."""
    def rep(m):
        tok, p, sp, ch = m.groups()
        if p == ".":
            if tok.endswith(".") or tok.lower().rstrip(".") in ABBR_NOCAP or re.fullmatch(r"(?:[A-Za-z]\.)*[A-Za-z]", tok):
                return m.group(0)
        return tok + p + sp + ch.upper()
    return re.sub(r"(\S+?)([.?])(\s+)([a-z])", rep, s)


def tidy_ws(s, fired):
    o = s
    s = s.replace(" ", " ").replace("​", "")
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\s+([,.;:!?])(?=\s|$)", r"\1", s)
    s = re.sub(r"(?<=[A-Za-z])([,;])(?=[A-Za-z])", r"\1 ", s)
    s = re.sub(r"(?<=[a-z]{2})\.(?=[A-Z][a-z])", ". ", s)
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    s = s.strip(" \t")
    if s != o:
        fired.add("spacing")
    return s


def punct(s, fired):
    o = s
    s = re.sub(r"!+(?![\[=])", ".", s)           # shout marks; keep markdown images ![..] and != intact
    s = re.sub(r"\?{2,}", "?", s)
    s = re.sub(r"\.{4,}", "...", s)               # long runs become one ellipsis
    s = re.sub(r",{2,}", ",", s)
    s = re.sub(r"(?<![.\d])\.\.(?!\.)", ".", s)   # a doubled period is a typo; an ellipsis (...) is kept
    s = re.sub(r"\s*&\s*(?=[A-Za-z])", lambda m: " and " if " & " in m.group(0) else m.group(0), s)
    if s != o:
        fired.add("punctuation")
    return s


def fix_a_an(s, fired):
    def rep(m):
        art, word = m.group(1), m.group(2)
        lw = word.lower()
        if len(word) > 1 and word.isupper() and word.isalpha():   # acronym: letter-name sound
            want = "an" if word[0] in AN_LETTERS else "a"
        elif lw in STRICT_AN or lw.startswith(("honest", "hour")):
            want = "an"
        elif lw in STRICT_A or lw.startswith(("uni", "use", "eu", "one")):
            want = "a"
        else:
            want = "an" if lw[0] in "aeiou" else "a"
        if art.lower() == want:
            return m.group(0)
        fired.add("a/an")
        return case_like(art, want) + " " + word
    return re.sub(r"\b([Aa]n?)\s+([A-Za-z][A-Za-z0-9]*)", rep, s)


def dedupe(s, fired):
    ok = {"had", "that"}

    def rep(m):
        if m.group(1).lower() in ok:
            return m.group(0)
        fired.add("duplicate word")
        return m.group(1)
    return re.sub(r"\b([A-Za-z]+)\s+\1\b(?!['’-])", rep, s, flags=re.I)


def remove_filler(s, ctx, fired):
    pat = re.compile(r"\b(" + "|".join(FILLER) + r")\s+", re.I)
    out = pat.sub("", s)
    if out != s:
        fired.add("tone: filler removed")
        out = cap_sentences(out)
        if s[:1].isupper() and out[:1].islower():
            out = out[0].upper() + out[1:]
    return out


def is_shouting(s):
    letters = re.sub(r"[^A-Za-z]", "", s)
    return len(letters) > 8 and s == s.upper() and len(s.split()) > 1


def upper_acronyms(w):
    return re.sub(r"[A-Za-z0-9]+", lambda m: m.group(0).upper() if m.group(0).upper() in ACRONYMS else m.group(0), w)


def keep_word(w, all_caps_src, ctx):
    core = re.sub(r"[^\w]", "", w)
    if core.lower() in ctx.keep:
        return True
    if core.upper() in ACRONYMS:
        return True
    if re.search(r"\d", core) and not core.isdigit():
        return True
    if not all_caps_src and ((core.isupper() and len(core) > 1) or re.search(r"[a-z][A-Z]", core)):
        return True
    if all_caps_src and re.search(r"[a-z][A-Z]", core):
        return True
    return False


def title_case(s, ctx, fired):
    orig = s
    s = re.sub("([\u0000\u0001]\\d+[\u0000\u0001])", r" \1 ", s)        # a protected span (HTML tag, code) is its own word
    shout = is_shouting(s)
    words = s.split(" ")
    out = []
    idxs = [i for i, w in enumerate(words) if LETTER.search(w)]
    first, last = (idxs[0], idxs[-1]) if idxs else (-1, -1)
    after_colon = False
    for i, w in enumerate(words):
        if not LETTER.search(w):
            out.append(w); continue
        if keep_word(w, shout, ctx):
            core = re.sub(r"[^\w]", "", w)
            nw = upper_acronyms(w) if core.lower() not in ctx.keep else w
        else:
            parts = re.split(r"(-|/)", w)
            res = []
            for p in parts:
                if p in ("-", "/") or not p:
                    res.append(p); continue
                bare = re.sub(r"[^A-Za-z.']", "", p).lower()
                m = re.match(r"^([^A-Za-z0-9]*)(.*)$", p)
                pre, body = m.group(1), m.group(2)
                if bare in SMALL and not (i == first or i == last or after_colon):
                    res.append(pre + body.lower())
                elif keep_word(body, shout, ctx):
                    res.append(upper_acronyms(p))
                else:
                    res.append(pre + body[:1].upper() + body[1:].lower() if (shout or body.islower() or body[:1].islower()) else p)
            nw = "".join(res)
        after_colon = w.endswith(":") or w in ("-", "–", "—")
        out.append(nw)
    r = re.sub(" ([\u0000\u0001]\\d+[\u0000\u0001]) ", r"\1", " ".join(out))
    if r != orig:
        fired.add("title case")
    return r


def sentence_case(s, ctx, fired):
    shout = is_shouting(s)
    o = s
    if shout:
        s = " ".join(w if keep_word(w, True, ctx) else w.lower() for w in s.split(" "))
        s = re.sub(r"\bi\b", "I", s)
    if shout:
        s = re.sub(r"\b(january|february|april|june|july|september|october|november|december|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                   lambda m: m.group(1).capitalize(), s)
    s = re.sub(r"\bi\b(?=[ ',.])", "I", s)
    s = cap_sentences(s)
    s = re.sub(r"^([a-z])", lambda m: m.group(1).upper(), s)
    if s != o:
        fired.add("capitalization")
    return s


def expand_abbr(s, fired):
    def rep(m):
        w = m.group(0)
        if w.lower() in ABBR_EXPAND:
            fired.add("abbreviation expanded")
            return ABBR_EXPAND[w.lower()]
        return w
    return re.sub(r"[A-Za-z]+", rep, s)


def decode_code_style(s, fired):
    if re.search(r"[A-Za-z0-9]_[A-Za-z0-9]", s):
        fired.add("code-style name")
        return re.sub(r"(?<=[A-Za-z0-9])_(?=[A-Za-z0-9])", " ", s)
    if re.fullmatch(r"[a-z]+(?:[A-Z][a-z0-9]+)+", s):
        fired.add("code-style name")
        return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    return s


# ---------------------------------------------------------------- pipeline
def _core_rules(core, kind, prefix, ctx, fired, review):
    """Rules shared by every kind, applied to text with protected spans already replaced."""
    if kind in ("title", "label"):
        core = decode_code_style(core, fired)
    if EMOJI.search(core):
        core = EMOJI.sub("", core); fired.add("emoji removed")
    core = core.replace("’", "'")
    core = tidy_ws(core, fired)
    core = punct(core, fired)
    core = word_sub(core, SPELL, ctx, "US spelling", fired)
    core = word_sub(core, TYPOS, ctx, "typo", fired)
    if ctx.tone:
        core = word_sub(core, CONTR, ctx, "tone: contraction expanded", fired)
        core = word_sub(core, INFORMAL, ctx, "tone: informal wording", fired)
        core = remove_filler(core, ctx, fired)
    core = fix_a_an(core, fired)
    core = dedupe(core, fired)
    if kind == "cell":
        return core
    if kind == "title" or (kind == "text" and prefix.startswith("#")):
        core = expand_abbr(core, fired)
        if ctx.titlecase:
            core = title_case(core, ctx, fired)
        for w in re.findall(r"[A-Za-z]+", core):
            if w.lower() in AMBIGUOUS_ABBR:
                review.append(f"ambiguous abbreviation '{w}'")
    elif kind == "label":
        core = expand_abbr(core, fired)
        if ctx.titlecase and (is_shouting(core) or core == core.lower() and len(core) < 60):
            core = title_case(core, ctx, fired)
    else:
        if is_shouting(core) and re.search(r"\b(MAY|MARCH|AUGUST)\b", core):
            review.append("check capitalization of 'May', 'March' or 'August' (a month name or an ordinary word)")
        core = sentence_case(core, ctx, fired)
        words = len(re.findall(r"[A-Za-z]+", core))
        bold_label = re.fullmatch(r"(\*\*|__)[^*_]+\1:?", core.strip())     # a wholly bold line works as a heading
        if (words >= 4 and not bold_label and not re.search(r"[.?:;)…\"'\]|>\u0001]$", core.rstrip())
                and prefix.strip() not in ("-", "*", "+") and not re.match(r"^\d", prefix)):
            core += "."; fired.add("terminal period")
    return tidy_ws(core, set())


def _protect(core):
    holders = []

    def hold(mo):                                         # HTML tags get their own marker so a line ending in one gets no period
        holders.append(mo.group(0)); m = "\u0001" if mo.group(0).startswith("<") else "\u0000"
        return f"{m}{len(holders) - 1}{m}"
    return PROTECT.sub(hold, core), holders


def _restore(core, holders):
    for i, h in enumerate(holders):
        core = core.replace(f"\u0000{i}\u0000", h).replace(f"\u0001{i}\u0001", h)
    return core


def _once(text, kind, ctx):
    fired, review = set(), []
    if not text or not text.strip():
        return text, fired, review
    m = re.match(r"^(\s*)(.*?)(\s*)$", text, re.S)
    lead, core, tail = m.groups()
    tail = tail.replace(" ", "").replace("\t", "")
    if kind in ("title", "label") and FUNC_NAME.match(core.strip()):
        return text, fired, ["auto-generated field name: set a readable display name"]
    if kind == "text":
        if re.match(r"^(```|~~~)", core) or (re.match(r"^( {4,}|\t)", lead.replace("\n", "")) and not re.match(r"^([-*+]|\d+[.)])\s", core)):
            return text, fired, review                          # code fence or indented code block
        if re.match(r"^<[^>]+>.*$", core) and core.rstrip().endswith(">"):
            return text, fired, review                          # raw HTML line
        if core.startswith("|"):                                # markdown table row: fix each cell only
            if re.fullmatch(r"[\s|:\-]+", core) and "-" in core:
                return text, fired, review
            cells = core.split("|")
            for i in range(1, len(cells) - 1 if cells[-1].strip() == "" else len(cells)):
                inner = cells[i].strip()
                if inner:
                    c, holders = _protect(inner)
                    cells[i] = " " + _restore(_core_rules(c, "cell", "", ctx, fired, review), holders) + " "
            br = "  " if re.search(r"\|( {2,})$", text.rstrip("\n\r")) else ""
            return lead + "|".join(cells).rstrip() + br + tail, fired, review
    marker = re.match(r"^((?:#{1,6}|[-*+]|\d+[.)]|>)\s+)", core) if kind == "text" else None
    prefix = ""
    if marker:
        prefix, core = marker.group(1), core[marker.end():]
    core, holders = _protect(core)
    core = _core_rules(core, kind, prefix, ctx, fired, review)
    for w in re.findall(r"[A-Za-z]+", core):
        if w.lower() in HYPE:
            review.append(f"informal or vague word '{w}': reword in a professional, narrative tone")
    core = _restore(core, holders)
    if kind == "text":
        br = "  " if re.search(r"( {2,})$", text.rstrip("\n\r")) else ""
        return lead + prefix + core + br + tail, fired, review
    return core.strip(), fired, review


def process(text, kind, ctx):
    """kind: title | label | description | text. Returns (new_text, rules_fired, needs_review).
    Rules run to a fixed point (at most 4 passes) so a second run never changes the result."""
    out, fired, review = text, set(), []
    for _ in range(4):
        new, f, rv = _once(out, kind, ctx)
        fired |= f
        review += [r for r in rv if r not in review]      # keep notes raised in earlier passes
        if new == out:
            break
        out = new
    return out, fired, review


class MdState:
    """Per-widget state carried across `lines` so fenced code blocks are skipped."""
    def __init__(self):
        self.fence = False

    def line(self, text, ctx):
        if re.match(r"^\s*(```|~~~)", text):
            self.fence = not self.fence
            return text, set(), []
        if self.fence:
            return text, set(), []
        return process(text, "text", ctx)


# ---------------------------------------------------------------- JSON traversal
SKIP_KEYS = {"queryLines", "expression", "fieldName", "name", "query", "parameters", "mappings", "value", "values",
             "color", "colors", "url", "datasetName", "scale", "format"}


def classify(path_parts):
    """Return kind for a leaf string path, or None when it is not user-facing."""
    if not path_parts or any(p in SKIP_KEYS for p in path_parts):
        return None
    last = path_parts[-1]
    if "multilineTextboxSpec" in path_parts and "lines" in path_parts and isinstance(last, int):
        return "text"
    if last == "displayName":
        return "label" if path_parts[0] == "datasets" else "title"
    if last == "title":
        return "title"
    if last in ("description", "subtitle", "tooltip"):
        return "description"
    return None


def walk(o, parts=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, parts + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, parts + (i,))
    elif isinstance(o, str):
        yield parts, o


def fmt_path(parts):
    s = ""
    for p in parts:
        s += f"[{p}]" if isinstance(p, int) else (("." if s else "") + p)
    return s


def parse_path(s):
    parts = []
    for m in re.finditer(r"\[(\d+)\]|([^.\[\]]+)", s):
        parts.append(int(m.group(1)) if m.group(1) is not None else m.group(2))
    return parts


def get_parent(d, parts):
    for p in parts[:-1]:
        d = d[p]
    return d


# ---------------------------------------------------------------- byte-preserving writer
_WS = re.compile(r"\s*")
_STR = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
_SCALAR = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null")


def index_strings(raw):
    """Map JSON path -> (start, end) of every string value in the raw text, so edits can be spliced in
    without re-serializing the file (numbers, spacing, escapes and line endings stay byte-identical)."""
    pos, out = 0, {}

    def skip():
        nonlocal pos
        pos = _WS.match(raw, pos).end()

    def value(path):
        nonlocal pos
        skip()
        c = raw[pos]
        if c == "{":
            pos += 1; skip()
            if raw[pos] == "}":
                pos += 1; return
            while True:
                skip(); m = _STR.match(raw, pos); key = json.loads(m.group(0)); pos = m.end(); skip()
                pos += 1                                   # ':'
                value(path + (key,)); skip()
                if raw[pos] == ",":
                    pos += 1; continue
                pos += 1; return                           # '}'
        elif c == "[":
            pos += 1; skip()
            if raw[pos] == "]":
                pos += 1; return
            i = 0
            while True:
                value(path + (i,)); i += 1; skip()
                if raw[pos] == ",":
                    pos += 1; continue
                pos += 1; return                           # ']'
        elif c == '"':
            m = _STR.match(raw, pos); out[path] = (m.start(), m.end()); pos = m.end()
        else:
            pos = _SCALAR.match(raw, pos).end()
    value(())
    return out


def patch(raw, edits):
    spans = index_strings(raw)
    missing = [p for p in edits if p not in spans]
    for s, e, new in sorted(((*spans[p], new) for p, new in edits.items() if p in spans), reverse=True):
        raw = raw[:s] + json.dumps(new, ensure_ascii=False) + raw[e:]
    return raw, missing


def find_files(p):
    p = Path(p)
    return [p] if p.is_file() else sorted(p.rglob("*.lvdash.json"))


def load(f):
    """Return (raw_text, data, had_bom) or None (with a message on stderr) when the file cannot be read."""
    try:
        b = f.read_bytes()
        bom = b.startswith(b"\xef\xbb\xbf")
        raw = b.decode("utf-8-sig")
        return raw, json.loads(raw), bom
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"skip: {f} is not valid UTF-8 JSON ({e})", file=sys.stderr)
        return None


def resolve_inputs(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"error: path not found: {path}")
    files = find_files(p)
    if not files:
        sys.exit(f"error: no *.lvdash.json files found under {path}")
    return files


COPIES_DIR = "dashboard_verbiage_fix"
KIND = {"bar": "bar chart", "line": "line chart", "area": "area chart", "pie": "pie chart", "scatter": "scatter plot",
        "combo": "combo chart", "counter": "counter", "table": "table", "pivot": "pivot table", "choropleth-map": "map",
        "custom-vega-viz": "custom chart", "filter-single-select": "single-select filter",
        "filter-multi-select": "multi-select filter", "filter-date-range-picker": "date range filter"}
ELEMENT = {"displayName": "label", "title": "title", "description": "description"}


def plain(v):
    """Display text without markdown or HTML markup, for describing where a string sits."""
    if isinstance(v, dict):
        v = v.get("value", v.get("text"))
    if not isinstance(v, str):
        return ""
    v = re.sub(r"!\[[^\]]*\]\([^)]*\)|<[^>]+>", " ", v)
    v = re.sub(r"^\s*(?:#+|[-*]|\d+\.)\s+", "", v).replace("**", "").replace("__", "")
    v = re.sub(r"\s+", " ", v).strip()
    return v if len(v) <= 60 else v[:59].rstrip() + "…"


def locate(data, parts):
    """(page name, location in plain words) for a string's JSON path, so a reader can find it on the dashboard."""
    def at(o, k):
        return o[k] if isinstance(o, dict) and k in o or isinstance(o, list) and isinstance(k, int) and 0 <= k < len(o) else None
    if not parts:
        return "", ""
    if parts[0] == "datasets":
        ds = at(at(data, "datasets"), parts[1]) if len(parts) > 1 else None
        return "(no page: dataset)", f"Dataset '{plain(at(ds, 'displayName')) or at(ds, 'name') or parts[1]}'"
    if parts[0] != "pages" or len(parts) < 2:
        return "", fmt_path(parts)
    page = at(at(data, "pages"), parts[1])
    pname = plain(at(page, "displayName")) or str(at(page, "name") or f"page {parts[1] + 1}")
    if len(parts) < 4 or parts[2] != "layout":
        return pname, "Page name" if parts[-1] == "displayName" else fmt_path(parts[2:])
    w = at(at(at(page, "layout"), parts[3]), "widget") or {}
    if "multilineTextboxSpec" in w:
        lines = [l for l in (at(at(w, "multilineTextboxSpec"), "lines") or []) if isinstance(l, str)]
        i = parts[-1] if isinstance(parts[-1], int) and parts[-2] == "lines" else 0
        head = next((plain(l) for l in reversed(lines[:i + 1]) if re.match(r"\s*#+\s", l) and plain(l)), "")
        first = next((plain(l) for l in lines if plain(l)), "")
        return pname, f"Text box, under heading '{head}'" if head else f"Text box starting '{first}'"
    spec = at(w, "spec") or {}
    wt = at(spec, "widgetType") or "widget"
    kind = KIND.get(wt) or ("filter" if str(wt).startswith("filter") else str(wt).replace("-", " "))
    title = plain(at(at(spec, "frame"), "title"))
    where = f"'{title}' ({kind})" if title else f"Untitled {kind}"
    tail = [x for x in parts[4:] if isinstance(x, str)]
    if "encodings" in tail:
        ch = next((x for x in tail[tail.index("encodings") + 1:] if x not in ("columns", "fields")), "")
        elem = f"{ch} axis label" if ch in ("x", "y") else f"{ch} label" if ch else "column label"
    else:
        elem = ELEMENT.get(tail[-1], tail[-1]) if tail else "text"
    return pname, f"{where} › {elem}"


# ---------------------------------------------------------------- commands
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


def cmd_extract(a):
    rows, bad = [], 0
    for f in resolve_inputs(a.path):
        ld = load(f)
        if ld is None:
            bad += 1; continue
        for parts, text in walk(ld[1]):
            kind = classify(parts)
            if kind:
                rows.append({"file": str(f), "path": fmt_path(parts), "kind": kind, "text": text})
    out = json.dumps(rows, indent=2, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(out + "\n", encoding="utf-8"); print(f"{len(rows)} strings -> {a.out}")
    else:
        print(out)
    return 1 if bad else 0


def run_changes(a, files, changes_fn):
    all_rows, bad, written = [], 0, 0
    root = Path(a.path) if Path(a.path).is_dir() else Path(a.path).parent
    copies = None if a.write or a.cmd != "fix" or a.no_copies else Path(a.copies_dir or COPIES_DIR)
    if copies and Path(a.path).resolve().is_relative_to(copies.resolve()):
        copies = None                                         # already running on the fixed set: never copy onto itself
    if copies:                                                # do not re-read earlier copies as inputs
        files = [f for f in files if not f.resolve().is_relative_to(copies.resolve())]
    copied = changed_files = 0
    for f in files:
        ld = load(f)
        if ld is None:
            bad += 1; continue
        raw, data, bom = ld
        rows = changes_fn(f, data)
        for r in rows:
            r["page"], r["location"] = locate(data, r["_parts"])
        all_rows += rows
        edits = {tuple(r["_parts"]): r["after"] for r in rows if r["before"] != r["after"]}
        new_raw = raw
        if edits:
            new_raw, missing = patch(raw, edits)
            for m in missing:
                print(f"skip: {f} {fmt_path(m)} could not be located in the file", file=sys.stderr)
        if edits and a.write:
            f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new_raw.encode("utf-8"))
            written += 1
        if copies:                                            # the full set, fixed where needed; originals untouched
            out = copies / f.resolve().relative_to(root.resolve())
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new_raw.encode("utf-8"))
            copied += 1; changed_files += bool(edits)
    shown = [{k: v for k, v in r.items() if not k.startswith("_")} for r in all_rows]
    report = a.report or (None if a.no_report else report_name(
        a.path, files, ("Wording Fixes" if a.cmd == "fix" else "Wording Rewrites") + (" (Applied)" if a.write else " (Proposed)"), "csv"))
    if report:
        with open(report, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["file", "page", "location", "path", "kind", "before", "after", "rules", "needs_review"])
            w.writeheader(); w.writerows(shown)
    for r in shown:
        print(f"{r['file']}  {r['path']}\n   at {r['page']} › {r['location']}\n   - {r['before']!r}\n   + {r['after']!r}   [{r['rules']}]"
              + (f"  REVIEW: {r['needs_review']}" if r["needs_review"] else ""))
    changed = sum(1 for r in all_rows if r["before"] != r["after"])
    flagged = sum(1 for r in all_rows if r["needs_review"])
    mode = f"written to {written} file(s)" if a.write else "dry run, nothing written (use --write)"
    print(f"\n{changed} change(s), {flagged} item(s) with a REVIEW note, in {len({r['file'] for r in shown})} file(s); {mode}.")
    if report:
        print(f"Report -> {report}")
    if copies:
        print(f"Fixed copies -> {copies}/ ({copied} file(s), {changed_files} with changes); originals unchanged")
    return 1 if bad else 0


def cmd_fix(a):
    ctx = Ctx(keep=[k for k in (a.keep or "").split(",") if k], tone=not a.no_tone, titlecase=not a.no_titlecase)

    def changes(f, data):
        rows, states = [], {}
        for parts, text in walk(data):
            kind = classify(parts)
            if not kind:
                continue
            if kind == "text":
                new, fired, review = states.setdefault(parts[:-1], MdState()).line(text, ctx)
            else:
                new, fired, review = process(text, kind, ctx)
            if new != text or review:
                rows.append({"file": str(f), "path": fmt_path(parts), "kind": kind, "before": text, "after": new,
                             "rules": ", ".join(sorted(fired)), "needs_review": "; ".join(review), "_parts": parts})
        return rows
    return run_changes(a, resolve_inputs(a.path), changes)


def match_file(spec, files, root):
    """Files an edit's "file" value refers to: full/relative path first, else a unique base name."""
    sp = Path(spec)
    exact = [f for f in files if f.resolve() == sp.resolve() or f.resolve() == (Path(root) / sp).resolve()
             or f.as_posix().endswith("/" + sp.as_posix().lstrip("./"))]
    if exact:
        return exact if len(sp.parts) > 1 else [f for f in exact if f.name == sp.name]
    named = [f for f in files if f.name == sp.name]
    return named


def cmd_apply(a):
    edits = json.loads(Path(a.edits).read_text(encoding="utf-8-sig"))
    files = resolve_inputs(a.path)
    root = Path(a.path) if Path(a.path).is_dir() else Path(a.path).parent
    by_file = {}
    for e in edits:
        hit = match_file(e["file"], files, root)
        if len(hit) != 1:
            print(f"skip: {e['file']} {e.get('path', '')}: " + ("not found" if not hit else "ambiguous file name; use a longer path"), file=sys.stderr)
            continue
        by_file.setdefault(hit[0], []).append(e)

    def changes(f, data):
        rows = []
        for e in by_file.get(f, []):
            parts = parse_path(e["path"])
            try:
                cur = get_parent(data, parts)[parts[-1]]
            except (KeyError, IndexError, TypeError):
                print(f"skip: {f.name} {e['path']} not found", file=sys.stderr); continue
            if "old" in e and e["old"] != cur:
                print(f"skip: {f.name} {e['path']} changed since review", file=sys.stderr); continue
            if not isinstance(cur, str) or not classify(parts):
                print(f"skip: {f.name} {e['path']} is not user-facing text", file=sys.stderr); continue
            if cur != e["new"]:
                rows.append({"file": str(f), "path": e["path"], "kind": classify(parts), "before": cur, "after": e["new"],
                             "rules": "reviewed rewrite", "needs_review": "", "_parts": tuple(parts)})
        return rows
    return run_changes(a, files, changes)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("path"); e.add_argument("-o", "--out"); e.set_defaults(fn=cmd_extract)
    for name, fn in (("fix", cmd_fix), ("apply", cmd_apply)):
        p = sub.add_parser(name); p.add_argument("path")
        if name == "apply":
            p.add_argument("edits")
        p.add_argument("--write", action="store_true", help="modify files (default is a dry run)")
        p.add_argument("--report", help="CSV of every change (default: '<dashboards> - Wording Fixes (Proposed) - <date>.csv', "
                                        "'Applied' with --write, 'Wording Rewrites' for apply)")
        p.add_argument("--no-report", action="store_true", help="do not write the CSV report")
        if name == "fix":
            p.add_argument("--copies-dir", help=f"folder for the fixed copies of a dry run (default: {COPIES_DIR})")
            p.add_argument("--no-copies", action="store_true", help="dry run without writing fixed copies")
        if name == "fix":
            p.add_argument("--keep", help="comma-separated words to leave untouched (brand names, proper nouns)")
            p.add_argument("--no-tone", action="store_true", help="skip tone rewrites (contractions, informal words and filler stay)")
            p.add_argument("--no-titlecase", action="store_true", help="do not re-case titles")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
