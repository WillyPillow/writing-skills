#!/usr/bin/env python3
"""Mechanical review triggers for the technical-writing skill.

The script reads raw text and assumes no markup, so it works on Markdown,
LaTeX, reStructuredText, plain text, or text extracted from a PDF. Markup
that leaks into a check shows up as noise, not as an error.

It runs in one of two profiles:

  strict     (default) Checks whose hits are almost always worth looking at.
  reference  Every check, including noisy ones. The extra hits are places to
             look, not errors.

The script only reports. It never edits the input, and it exits with status 0
whatever it finds, because a clean run says nothing about substance or
argument. See SKILL.md, section 7.

Examples:

  check.py draft.md --source notes/ --source results.csv
  check.py draft.tex --profile reference --known SLO,QPS
  pdftotext paper.pdf - | check.py - --known-file glossary.txt
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation

STRICT = "strict"
REFERENCE = "reference"

NOT_CHECKED = (
    "This script does not check substance or argument: whether claims have "
    "context and evidence, whether steps are motivated, whether citations are "
    "positioned, whether decision records are complete, or whether decision "
    "history was invented. It also does not check anything that depends on "
    "markup: unused figures, tables and equations by label, citation keys, "
    "formula punctuation, headings, bold and bullets. Those stay with the "
    "reviewer (SKILL.md, section 7)."
)

REFERENCE_BANNER = (
    "The checks below have frequent false positives. Treat each hit as a "
    "place to look, not as an error. Do not rewrite a sentence only to clear "
    "a hit, and never replace a flagged word with a synonym."
)


# ---------------------------------------------------------------------------
# Text model


class Document:
    def __init__(self, name, text):
        self.name = name
        self.text = text
        self.line_starts = [0] + [m.end() for m in re.finditer(r"\n", text)]
        self.urls = mask(text, URL_RE)
        self._sentences = None
        self._paragraphs = None

    def line_of(self, offset):
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def snippet(self, start, end=None, width=40):
        end = start if end is None else end
        a = max(0, start - width)
        b = min(len(self.text), end + width)
        s = " ".join(self.text[a:b].split())
        return ("..." if a > 0 else "") + s + ("..." if b < len(self.text) else "")

    @property
    def paragraphs(self):
        if self._paragraphs is None:
            self._paragraphs = list(split_paragraphs(self.text))
        return self._paragraphs

    @property
    def sentences(self):
        if self._sentences is None:
            self._sentences = []
            for p_start, p_end in self.paragraphs:
                self._sentences.append(list(split_sentences(self.text, p_start, p_end)))
        return self._sentences

    def all_sentences(self):
        for para in self.sentences:
            yield from para


URL_RE = re.compile(r"(?:https?://|www\.)\S+|\b[\w.-]+\.(?:com|org|net|io|dev|edu|gov)(?:/\S*)?")


def mask(text, regex):
    """Return text with every match of regex replaced by spaces."""
    return regex.sub(lambda m: re.sub(r"\S", " ", m.group(0)), text)


def split_paragraphs(text):
    start = 0
    for m in re.finditer(r"\n[ \t]*\n\s*", text):
        if text[start:m.start()].strip():
            yield start, m.start()
        start = m.end()
    if text[start:].strip():
        yield start, len(text.rstrip())


# A line that starts a list item, a heading, or a rule ends the previous
# sentence even without punctuation.
BLOCK_START_RE = re.compile(
    r"\n(?=[ \t]*(?:[-*+•]\s|\d+[.)]\s|#{1,6}\s|[=\-~^#*+`:]{3,}[ \t]*(?:\n|$)))"
)
SENTENCE_END_RE = re.compile(r"[.!?]+[\"'”’)\]]*(?=\s)")
NEVER_END = {
    "e.g", "i.e", "cf", "vs", "fig", "figs", "eq", "eqs", "eqn", "sec", "secs",
    "no", "nos", "al", "dr", "mr", "mrs", "prof", "st", "ch", "pp", "vol",
    "ref", "refs", "thm", "viz", "approx", "resp", "ca", "ibid",
}


def split_sentences(text, start, end):
    """Yield (offset, sentence) pairs for the paragraph text[start:end]."""
    para = text[start:end]
    cuts = []
    for m in SENTENCE_END_RE.finditer(para):
        before = re.search(r"([A-Za-z.]+)$", para[: m.start()])
        word = before.group(1).lower().strip(".") if before else ""
        rest = para[m.end():].lstrip()
        if word in NEVER_END:
            continue
        if len(word) == 1 and word.isalpha() and before.group(1).isupper():
            continue  # an initial, as in "J. Williams"
        if word == "etc" and rest[:1].islower():
            continue
        cuts.append(m.end())
    cuts.extend(m.start() for m in BLOCK_START_RE.finditer(para))
    pos = 0
    for cut in sorted(set(cuts)) + [len(para)]:
        chunk = para[pos:cut]
        stripped = chunk.strip()
        if stripped:
            yield start + pos + (len(chunk) - len(chunk.lstrip())), stripped
        pos = cut


WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’]*(?:-[A-Za-z]+)*")


def words(s):
    return WORD_RE.findall(s)


def has_digit(s):
    return any(c.isdigit() for c in s)


# ---------------------------------------------------------------------------
# Check registry


class Finding:
    def __init__(self, offset, message):
        self.offset = offset
        self.message = message


CHECKS = []


def check(name, profile, description, needs=None):
    def register(func):
        CHECKS.append(
            {"name": name, "profile": profile, "description": description,
             "func": func, "needs": needs}
        )
        return func
    return register


def phrase_check(name, profile, description, patterns, message, flags=re.I,
                 unless_digit=False):
    """Register a check that flags every match of any pattern.

    With unless_digit, a match is skipped when its sentence contains a digit,
    for rules such as "scalable without a number".
    """
    compiled = [re.compile(p, flags) for p in patterns]

    def run(doc, ctx):
        text = doc.urls
        if unless_digit:
            for offset, sent in doc.all_sentences():
                masked = text[offset:offset + len(sent)]
                if has_digit(sent):
                    continue
                for rx in compiled:
                    for m in rx.finditer(masked):
                        yield Finding(offset + m.start(), message.format(m=m.group(0)))
            return
        for rx in compiled:
            for m in rx.finditer(text):
                yield Finding(m.start(), message.format(m=m.group(0)))

    check(name, profile, description)(run)


# ---------------------------------------------------------------------------
# Strict checks


@check("todo", STRICT, "Leftover TODO, TBD and FIXME markers.")
def check_todo(doc, ctx):
    for m in re.finditer(r"\[TODO\b[^\]]*\]|\b(?:TODO|TBD|FIXME)\b", doc.text):
        yield Finding(m.start(), f"unresolved marker \"{m.group(0)[:60]}\"")


# Numbers --------------------------------------------------------------------

UNIT = (
    r"%|×|x|[kKMGT]i?B|[kMG]bps|[kMG]Hz|Hz|ms|[µu]s|ns|secs?|s|mins?"
    r"|hrs?|h|d|px|pt|mm|cm|km|m|rps|qps|ops|[kKMGTB]"
)
DRAFT_NUM_RE = re.compile(
    r"(?<![\w.,/])(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?P<frac>\.\d+)?(?!\.\d)"
    r"(?:\s?(?P<unit>" + UNIT + r"))?(?!\w)"
)
SOURCE_NUM_RE = re.compile(
    r"(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?P<frac>\.\d+)?(?:\s?(?P<mult>[kKMGBT])(?![A-Za-z]))?"
)
MULTIPLIER = {"k": 3, "K": 3, "M": 6, "G": 9, "B": 9, "T": 12}
# Text spans whose numbers are not reported values: dates, clock times, list
# markers, and section numbers at the start of a line.
NUMBER_NOISE_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(?::\d{2})?\b"
    r"|^[ \t]*\d+[.)][ \t]|^[ \t]*\d+(?:\.\d+)+[ \t]+(?=[A-Z])",
    re.M,
)
# A number right after one of these words is a label, not a value.
LABEL_BEFORE_RE = re.compile(
    r"(?:\b(?:sections?|sec\.|chapters?|ch\.|figures?|fig\.|figs\.|tables?|tab\."
    r"|equations?|eqs?\.|eqn\.|appendix|steps?|items?|lines?|pages?|pp\.|p\."
    r"|footnotes?|theorems?|lemmas?|corollary|definitions?|propositions?|remarks?"
    r"|examples?|rules?|issues?|pr|pep|rfc|iso|version|v|no\.|phases?|stages?"
    r"|levels?|parts?|listings?|algorithms?|alg\.|claims?|cases?|options?)\s*"
    r"|§\s*|#)$",
    re.I,
)


def as_decimal(num, frac):
    try:
        return Decimal(num.replace(",", "") + (frac or "")).normalize()
    except InvalidOperation:
        return None


def source_values(texts):
    values = set()
    for text in texts:
        for m in SOURCE_NUM_RE.finditer(text):
            v = as_decimal(m.group("num"), m.group("frac"))
            if v is None:
                continue
            values.add(v)
            if m.group("mult"):
                values.add((v.scaleb(MULTIPLIER[m.group("mult")])).normalize())
    return values


def draft_candidates(v, unit):
    """Values that would count as the same number appearing in the source."""
    out = {v}
    if unit in MULTIPLIER:
        out.add(v.scaleb(MULTIPLIER[unit]).normalize())
    if unit == "%":
        out.add(v.scaleb(-2).normalize())
    if unit is None and v < 1:
        out.add(v.scaleb(2).normalize())
    return out


def is_minor_number(v, unit, frac):
    """Small counts and years: often not reported values, so reference only."""
    if unit or frac:
        return False
    return 0 <= v <= 10 or 1900 <= v <= 2099


def number_findings(doc, ctx, minor):
    known = ctx["source_values"]
    text = mask(doc.urls, NUMBER_NOISE_RE)
    seen = set()
    for m in DRAFT_NUM_RE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        if LABEL_BEFORE_RE.search(text[max(line_start, m.start() - 20):m.start()]):
            continue
        v = as_decimal(m.group("num"), m.group("frac"))
        if v is None:
            continue
        unit = m.group("unit")
        if is_minor_number(v, unit, m.group("frac")) != minor:
            continue
        if draft_candidates(v, unit) & known:
            continue
        shown = m.group(0)
        key = re.sub(r"\s", "", shown)
        if key in seen:
            continue
        seen.add(key)
        yield Finding(
            m.start(),
            f"\"{shown}\" does not appear in the source material; trace it to "
            f"the source or to a stated calculation, and do not change it "
            f"because of this flag",
        )


@check("numbers", STRICT,
       "Numbers that do not appear in the source material (needs --source).",
       needs="source")
def check_numbers(doc, ctx):
    return number_findings(doc, ctx, minor=False)


# Acronyms -------------------------------------------------------------------

# Acronyms any technical reader knows. Keep this list conservative: anything
# that depends on the field or the team goes in --known or --known-file.
BUILTIN_KNOWN = set("""
AI API ASCII CPU CSS CSV DNS FAQ GPU HTML HTTP HTTPS ID IDE IEEE IP ISO JSON
OK OS PDF PhD RAM RFC SDK SQL SSD SSH SSL TCP TLS UDP UI URI URL USB UTC UTF
UTF-8 XML YAML UK US USA EU CI CD CLI GB KB MB TB PB GHz MHz
MUST SHALL SHOULD MAY NOT REQUIRED RECOMMENDED OPTIONAL
TODO TBD FIXME NOTE WARNING
""".split())

ACRONYM_RE = re.compile(r"(?<![\w-])[A-Z][A-Za-z0-9]*(?:-[A-Z0-9]+)*(?![\w-]|\.\d)")
ROMAN_RE = re.compile(r"^[IVX]+$")


def acronym_key(token):
    """Return the acronym a token stands for, or None if it is not one."""
    base = token[:-1] if token.endswith("s") and len(token) > 2 else token
    if sum(c.isupper() for c in base) < 2 or any(c.islower() for c in base):
        return None
    if ROMAN_RE.match(base):
        return None
    return base


def shouting_line(line):
    ws = words(line)
    return len(ws) >= 3 and all(w.isupper() for w in ws)


def definition_offsets(text, acr):
    a = re.escape(acr)
    patterns = [
        r"\(\s*" + a + r"s?\s*\)",                       # long form (ACR)
        r"(?<![\w-])" + a + r"s?\s*\((?=[^()]*[a-z])[^()]*\s[^()]*\)",  # ACR (long form)
        r"(?<![\w-])" + a + r"s?,?\s+(?:stands for|is short for|short for|means)\b",
        r"(?m)^[ \t]*(?:[-*+]\s+)?" + a + r"s?\s*(?::|—|–| - )",  # glossary
    ]
    return sorted(m.start() for p in patterns for m in re.finditer(p, text))


# Characters that mark a token as code (an identifier, keyword or variable)
# when they touch it directly.
CODE_BEFORE = set("`_$@.\\/<{=:'\"")
CODE_AFTER = set("`_(=/\\>}'\"[")


def acronym_uses(doc):
    """Map each acronym to the offsets where it is used.

    Skips tokens that look like something other than an acronym: words in a
    line written all in capitals, tokens touching code punctuation, and
    capitalized forms of words that also appear in lowercase in the same
    document ("NONE" when "none" also appears), which are usually emphasis or
    code keywords.
    """
    text = doc.urls
    lower_words = set(re.findall(r"\b[a-z][a-z0-9]*\b", text))
    uses = defaultdict(list)
    lines = text.split("\n")
    for m in ACRONYM_RE.finditer(text):
        key = acronym_key(m.group(0))
        if key is None or key.lower() in lower_words:
            continue
        if text[m.start() - 1:m.start()] in CODE_BEFORE or text[m.end():m.end() + 1] in CODE_AFTER:
            continue
        if shouting_line(lines[doc.line_of(m.start()) - 1]):
            continue
        uses[key].append(m.start())
    return uses


@check("acronyms", STRICT,
       "Acronyms never defined, or used before their definition, unless known "
       "(built-in list, --known, --known-file).")
def check_acronyms(doc, ctx):
    known = ctx["known"]
    for acr, offsets in sorted(acronym_uses(doc).items(), key=lambda kv: kv[1][0]):
        if acr in known:
            continue
        defs = definition_offsets(doc.urls, acr)
        first = offsets[0]
        if not defs:
            yield Finding(first, f"\"{acr}\" is never defined; define it, or pass "
                                 f"it with --known if the reader knows it")
        elif defs[0] > first + len(acr) + 1 and doc.text[first - 1:first] != "(":
            yield Finding(first, f"\"{acr}\" is used before its definition on line "
                                 f"{doc.line_of(defs[0])}")


phrase_check(
    "stacked-hedges", STRICT,
    "Two hedges on one claim, such as \"may potentially\".",
    [r"\b(?:may|might|could|can)\s+(?:potentially|possibly|perhaps|conceivably)\b",
     r"\b(?:possibly|perhaps)\s+(?:may|might|could)\b"],
    "stacked hedge \"{m}\"; hedge once, where the uncertainty is",
)

phrase_check(
    "nominalizations", STRICT,
    "Verb phrases buried in nouns, such as \"performed an optimization of\".",
    [r"\b(?:perform|performs|performed|performing|conduct|conducts|conducted|"
     r"conducting|carry out|carries out|carried out|carrying out|make|makes|made|"
     r"making|undertake|undertook|undertaken)\s+(?:a|an|the)\s+\w+"
     r"(?:tion|sion|ment|ance|ence|ysis|isons?)\s+of\b"],
    "nominalization \"{m}\"; use the verb",
)

phrase_check(
    "stock-phrases", STRICT,
    "Stock phrases that carry no content, such as \"it is worth noting\".",
    [r"\bit(?: is|'s|’s) worth (?:noting|mentioning|pointing out)\b",
     r"\bit should be noted that\b",
     r"\bplays? an? (?:key|crucial|pivotal|vital|central|critical|important) role\b",
     r"\bdelv(?:e|es|ed|ing) (?:into|deeper)\b",
     r"\bin the (?:realm|landscape) of\b",
     r"\ba testament to\b",
     r"\bever-(?:evolving|changing|growing)\b",
     r"\bnavigat(?:e|es|ing) the complexit(?:y|ies)\b",
     r"\bunlock(?:s|ing)? the (?:full )?potential\b",
     r"\bpav(?:e|es|ed|ing) the way\b",
     r"\bin today['’]s (?:fast-paced|rapidly[- ]\w+|ever-\w+|digital|modern|"
     r"interconnected|data-driven)\b"],
    "stock phrase \"{m}\"; rewrite the sentence or delete it",
)

phrase_check(
    "vague-importance-clauses", STRICT,
    "Trailing participle clauses that assert importance, such as \", "
    "highlighting the importance of\".",
    [r",\s+(?:highlighting|underscoring|emphasi[sz]ing|showcasing|reflecting|"
     r"cementing|solidifying|marking|signal(?:l)?ing)\s+(?:the|its|their|a|an|our)?\s*"
     r"(?:\w+\s+)?(?:importance|significance|potential|commitment|value|power|"
     r"relevance|role)\b"],
    "trailing clause \"{m}\" asserts importance without showing it",
)


# ---------------------------------------------------------------------------
# Reference checks


@check("numbers-minor", REFERENCE,
       "Small counts (0-10) and years that do not appear in the source "
       "material (needs --source).",
       needs="source")
def check_numbers_minor(doc, ctx):
    return number_findings(doc, ctx, minor=True)


@check("defines-known", REFERENCE,
       "Definitions of acronyms passed with --known or --known-file, which the "
       "reader already knows.")
def check_defines_known(doc, ctx):
    for acr in sorted(ctx["user_known"]):
        for off in definition_offsets(doc.urls, acr)[:1]:
            yield Finding(off, f"\"{acr}\" is defined, but it was passed as known "
                               f"to the reader; never define what the reader knows")


phrase_check(
    "stock-vocabulary", REFERENCE,
    "Words common in LLM prose (section 5 list). Many have legitimate "
    "technical senses, such as \"robust estimator\".",
    [r"\b(?:pivotal|crucial|underscor(?:e|es|ed|ing)|landscape|realm|testament|"
     r"delv(?:e|es|ed|ing)|leverag(?:e|es|ed|ing)|utili[sz](?:e|es|ed|ing|ation)|"
     r"robust(?:ly|ness)?|seamless(?:ly)?|harness(?:es|ed|ing)?|unlock(?:s|ed|ing)?|"
     r"showcas(?:e|es|ed|ing)|nuanced|intricate|groundbreaking|game-changing|"
     r"cutting-edge|transformative|holistic|synerg(?:y|ies|istic))\b"],
    "stock word \"{m}\"; if the sentence says nothing without it, rewrite the "
    "sentence rather than swapping the word",
)

phrase_check(
    "unquantified-qualities", REFERENCE,
    "Design-doc qualities with no number in the sentence, such as "
    "\"scalable\" or \"best practices\".",
    [r"\b(?:scalab(?:le|ility)|flexib(?:le|ility)|extensib(?:le|ility)|"
     r"maintainab(?:le|ility)|future-proof|best practices?|performant|"
     r"high-performance|enterprise-grade|production-ready|battle-tested)\b"],
    "\"{m}\" with no number in the sentence; give the load, size or scenario",
    unless_digit=True,
)

phrase_check(
    "unquantified-intensifiers", REFERENCE,
    "Intensifiers with no number in the sentence, such as \"significantly "
    "improves\".",
    [r"\b(?:significantly|substantially|dramatically|drastically|greatly|vastly|"
     r"massively|highly|considerably|tremendously|enormously)\b"],
    "\"{m}\" with no number in the sentence; give the number and its baseline",
    unless_digit=True,
)

phrase_check(
    "self-superlatives", REFERENCE,
    "Superlatives about the work itself, such as \"novel\" or "
    "\"state-of-the-art\".",
    [r"\b(?:novel|state-of-the-art|state of the art|unprecedented|revolutionary|"
     r"best-in-class|world-class|first-ever|superior|elegant|powerful)\b",
     r"\b(?:we|this (?:paper|work|design|system|approach)) (?:is|are) the first\b"],
    "superlative \"{m}\"; state the specific property and its evidence",
)

phrase_check(
    "signposts", REFERENCE,
    "Sentences that announce the next step or the document layout instead of "
    "motivating it.",
    [r"\bwe now (?:turn to|discuss|present|describe|show|consider|introduce)\b",
     r"\bnaturally,? (?:one|we) (?:may |might |could )?(?:asks?|wonders?)\b",
     r"\bin this (?:section|chapter|subsection),? we\b",
     r"\bthe (?:rest|remainder) of this (?:paper|document|section|article|post) is\b",
     r"\bas (?:mentioned|discussed|noted|stated) (?:earlier|above|before|previously)\b",
     r"\blet us now\b|\blet's now\b|\blet’s now\b"],
    "signpost \"{m}\"; replace with the goal or obstacle that motivates the step",
)

phrase_check(
    "importance-adverbs", REFERENCE,
    "Sentence adverbs that announce importance, such as \"Importantly,\".",
    [r"\b(?:Importantly|Notably|Interestingly|Crucially|Remarkably),"],
    "\"{m}\" announces importance instead of showing it",
    flags=0,
)

phrase_check(
    "not-x-but-y", REFERENCE,
    "The \"not just X, but Y\" and \"it's not X, it's Y\" constructions.",
    [r"\bnot (?:just|merely|simply) [^.;:]{1,60}?,? but\b",
     r"\b(?:it|this|that)(?: is|'s|’s) not [^.;:]{1,40}?[,;—–]+\s*"
     r"(?:it|this|that)(?: is|'s|’s)\b"],
    "contrast construction \"{m}\"; state the claim directly",
)

phrase_check(
    "empty-monitoring", REFERENCE,
    "Failure plans that only promise monitoring, such as \"we will add "
    "monitoring\".",
    [r"\b(?:we will|we'll|we’ll|will|we plan to|we intend to)\s+(?:add|set up|"
     r"introduce|have|put in place|implement)\s+(?:\w+\s+)?(?:monitoring|alerting|"
     r"alerts|dashboards|observability)\b"],
    "\"{m}\"; say what is detected, what users see and how it recovers",
)

phrase_check(
    "logic-symbols", REFERENCE,
    "Logic symbols that should be words in running text (therefore, implies, "
    "for all, there exists).",
    [r"[∴∵⇒⇔⟹∀∃]"],
    "symbol \"{m}\"; in running text write the word",
    flags=0,
)

phrase_check(
    "assume-without-that", REFERENCE,
    "\"Assume A is ...\" without \"that\", which parses poorly.",
    [r"\b(?:Assume|Suppose|Note|Recall|Observe|Notice)\s+(?!that\b|the\b|we\b|you\b|"
     r"it\b|they\b|this\b|these\b|those\b|there\b)[A-Za-z][\w$\\{}^]*\s+(?:is|are|has|have)\b"],
    "\"{m}\"; add \"that\" after the verb",
    flags=0,
)


@check("long-sentences", REFERENCE,
       "Sentences over 25 words, the STE review trigger.")
def check_long_sentences(doc, ctx):
    for offset, sent in doc.all_sentences():
        n = len(words(sent))
        if n > 25:
            yield Finding(offset, f"sentence of {n} words; consider splitting it")


@check("long-paragraphs", REFERENCE, "Paragraphs over 150 words.")
def check_long_paragraphs(doc, ctx):
    for start, end in doc.paragraphs:
        n = len(words(doc.text[start:end]))
        if n > 150:
            yield Finding(start, f"paragraph of {n} words")


@check("passive-voice", REFERENCE,
       "Forms of \"be\" followed by a past participle. Matters most in "
       "procedures and design descriptions.")
def check_passive(doc, ctx):
    rx = re.compile(
        r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?"
        r"(?:\w+ed|built|chosen|done|driven|given|known|made|seen|shown|taken|"
        r"written|run|sent|kept|held|set|found|thought|left|lost|put|read|split)\b"
        r"(?!\s+(?:to|that)\b)",
        re.I,
    )
    for m in rx.finditer(doc.urls):
        yield Finding(m.start(), f"possible passive \"{m.group(0)}\"; name the actor "
                                 f"if it matters")


@check("em-dashes", REFERENCE, "Em dashes, which the section 5 list flags when frequent.")
def check_em_dashes(doc, ctx):
    rx = re.compile(r"—|(?<=\w)---(?=\w)|(?<=\w) -- (?=\w)")
    hits = list(rx.finditer(doc.text))
    n_words = len(words(doc.text)) or 1
    rate = 1000 * len(hits) / n_words
    if rate < 3:
        return
    for m in hits:
        yield Finding(m.start(), f"em dash ({rate:.1f} per 1000 words in this file)")


@check("rhetorical-questions", REFERENCE,
       "Sentences ending in a question mark, which may be rhetorical transitions.")
def check_questions(doc, ctx):
    for offset, sent in doc.all_sentences():
        if sent.rstrip("\"')]”’").endswith("?") and len(words(sent)) >= 3:
            yield Finding(offset, "question; if rhetorical, state the point instead")


@check("colon-reveals", REFERENCE,
       "Sentences ending in a short phrase after a colon, used for effect.")
def check_colon_reveals(doc, ctx):
    for offset, sent in doc.all_sentences():
        if len(re.findall(r":\s", sent)) != 1 or sent.count(":") != 1 or "\n" in sent:
            continue
        before, after = sent.split(":")
        if re.search(r"(?i)(follows|following|below|these|are|is)\s*$", before):
            continue
        # Only plain words after the colon; code or markup there is not a reveal.
        if not re.fullmatch(r"[\sA-Za-z,'’-]+[.!]\s*", after):
            continue
        if len(words(before)) >= 4 and 1 <= len(words(after)) <= 4:
            yield Finding(offset + len(before), "colon reveal; state it directly")


SUMMARY_OPENERS = re.compile(
    r"^(?:In short|In summary|In sum|Overall|Ultimately|Taken together|All in all|"
    r"In conclusion|To summari[sz]e|To sum up|In essence|Simply put|In other words)\b"
)


@check("closing-restatements", REFERENCE,
       "Paragraph-final sentences that open with a summary phrase and may "
       "restate the paragraph.")
def check_closing_restatements(doc, ctx):
    for para in doc.sentences:
        if len(para) >= 3 and SUMMARY_OPENERS.match(para[-1][1]):
            yield Finding(para[-1][0], "closing summary; delete it if it only "
                                       "restates the paragraph")


THEN_OPENERS = re.compile(r"^(?:Then|Thus|Hence|So|Therefore|We have|It follows)\b")


@check("then-thus-hence", REFERENCE,
       "Runs of three or more sentences opening with Then, Thus, Hence and the "
       "like, a sign the prose fails the blah test.")
def check_then_runs(doc, ctx):
    for para in doc.sentences:
        run = []
        for offset, sent in para + [(None, "")]:
            if offset is not None and THEN_OPENERS.match(sent):
                run.append(offset)
                continue
            if len(run) >= 3:
                yield Finding(run[0], f"{len(run)} sentences in a row open with "
                                      f"Then/Thus/Hence; say what each step is for")
            run = []


SYMBOL_START_RE = re.compile(
    r"^(?:\$|\\[A-Za-z]|[Α-ω]"
    r"|[A-Za-z](?:_\w+|\^\w+|'+)?\s+(?:is|are|was|has|have|can|must|denotes|equals|"
    r"satisfies|contains|belongs|lies|tends|converges)\b)"
)


@check("symbol-starts", REFERENCE,
       "Sentences that start with a symbol, such as \"$x$ is ...\" or \"n is the "
       "number of ...\".")
def check_symbol_starts(doc, ctx):
    for offset, sent in doc.all_sentences():
        if SYMBOL_START_RE.match(sent) and not sent.startswith("I "):
            yield Finding(offset, "sentence starts with a symbol; reword so it "
                                  "starts with a word")


@check("figure-mentioned-once", REFERENCE,
       "Figures and tables named by number only once, possibly only in their "
       "caption.")
def check_figures(doc, ctx):
    rx = re.compile(r"\b(Figure|Fig\.|Table|Listing|Diagram)\s+(\d+[a-z]?)\b")
    seen = defaultdict(list)
    for m in rx.finditer(doc.text):
        kind = "Figure" if m.group(1).startswith("Fig") else m.group(1)
        seen[(kind, m.group(2))].append(m.start())
    for (kind, num), offsets in seen.items():
        if len(offsets) == 1:
            yield Finding(offsets[0], f"{kind} {num} is mentioned once; check that "
                                      f"the text reads something off it")


@check("term-variants", REFERENCE,
       "One term spelled several ways: hyphenated, spaced or closed up, or "
       "with different internal capitals.")
def check_term_variants(doc, ctx):
    text = doc.urls
    lower = text.lower()
    for compound in sorted({m.group(0).lower() for m in
                            re.finditer(r"\b[A-Za-z]{2,}(?:-[A-Za-z]{2,})+\b", text)}):
        parts = compound.split("-")
        for variant in (" ".join(parts), "".join(parts)):
            m = re.search(r"\b" + re.escape(variant) + r"\b", lower)
            if m:
                yield Finding(m.start(), f"\"{text[m.start():m.end()]}\" and "
                                         f"\"{compound}\" both appear; pick one")
    # Words with internal capitals ("GitHub"), spelled another way elsewhere
    # ("Github"). All-capital forms are left out: they are usually emphasis.
    spellings = defaultdict(dict)
    for m in re.finditer(r"\b[A-Za-z]+\b", text):
        w = m.group(0)
        if not w.isupper():
            spellings[w.lower()].setdefault(w, m.start())
    for key, forms in sorted(spellings.items()):
        if len(forms) >= 2 and any(not f[1:].islower() for f in forms):
            yield Finding(min(forms.values()),
                          "spelled " + ", ".join(f"\"{f}\"" for f in forms) + "; pick one")


FUNCTION_WORDS = set("""
a an the this that these those some any each every no all both either neither
and or but nor so yet for of in on at by to from with without into onto over
under about above below between among through during before after since until
while as than like via per if then else when where which who whom whose what
why how whether because although though unless i we you he she it they me us
him her them my our your his its their mine ours yours theirs is are was were
be been being am do does did done has have had having can could may might
must shall should will would not also only just very more most less least
such same other another own there here up down out off again further once
""".split())
COMMON_VERBS = set("""
use uses used using make makes made run runs ran provide provides provided
allow allows allowed require requires required return returns returned take
takes took give gives gave get gets got need needs needed add adds added
call calls called see sees saw show shows showed know knows knew mean means
meant keep keeps kept let lets put puts set sets support supports supported
handle handles handled create creates created store stores stored send sends
sent read reads write writes wrote change changes changed contain contains
contained include includes included become becomes became seem seems seemed
help helps helped want wants wanted work works worked
""".split())


@check("noun-clusters", REFERENCE,
       "Runs of four or more content words with no function word, a rough "
       "stand-in for noun clusters over three words.")
def check_noun_clusters(doc, ctx):
    for offset, sent in doc.all_sentences():
        run = []
        for m in re.finditer(r"[A-Za-z][A-Za-z'’]*(?:-[A-Za-z]+)*|[^\sA-Za-z]+", sent):
            w = m.group(0)
            lw = w.lower()
            if not w[0].isalpha() or lw in FUNCTION_WORDS or lw in COMMON_VERBS \
                    or lw.endswith("ly") or w.isupper():
                if len(run) >= 4:
                    yield Finding(offset + run[0][0],
                                  f"\"{' '.join(x for _, x in run)}\"; break it up "
                                  f"with prepositions if it is a noun cluster")
                run = []
                continue
            run.append((m.start(), w))
        if len(run) >= 4:
            yield Finding(offset + run[0][0],
                          f"\"{' '.join(x for _, x in run)}\"; break it up with "
                          f"prepositions if it is a noun cluster")


# ---------------------------------------------------------------------------
# Driver


def read_text(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def iter_source_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                for name in sorted(files):
                    yield os.path.join(root, name)
        else:
            yield p


def read_source(path):
    try:
        with open(path, "rb") as f:
            data = f.read(50_000_000)
    except OSError as e:
        print(f"warning: cannot read source {path}: {e}", file=sys.stderr)
        return ""
    if b"\0" in data[:8192]:
        print(f"warning: skipping binary source {path}; extract its text first",
              file=sys.stderr)
        return ""
    return data.decode("utf-8", errors="replace")


def parse_known(values):
    out = set()
    for v in values:
        out.update(t for t in re.split(r"[\s,]+", v) if t)
    return out


def read_known_file(path):
    with open(path, encoding="utf-8") as f:
        return parse_known(line.split("#", 1)[0] for line in f)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="Run with --list-checks to see every check and its profile.",
    )
    ap.add_argument("files", nargs="*", help="text files to check; - reads stdin")
    ap.add_argument("--profile", choices=[STRICT, REFERENCE], default=STRICT,
                    help="strict (default): low false positives; reference: every "
                         "check, extra hits for reference only")
    ap.add_argument("--source", action="append", default=[], metavar="PATH",
                    help="the author's material (file or directory, repeatable); "
                         "enables the number checks")
    ap.add_argument("--known", action="append", default=[], metavar="LIST",
                    help="acronyms the reader knows, comma or space separated "
                         "(repeatable)")
    ap.add_argument("--known-file", action="append", default=[], metavar="PATH",
                    help="file of acronyms the reader knows, one or more per "
                         "line, # starts a comment")
    ap.add_argument("--no-builtin-known", action="store_true",
                    help="do not treat the built-in common acronyms as known")
    ap.add_argument("--max-per-check", type=int, default=30, metavar="N",
                    help="show at most N findings per check (0 for all; default 30)")
    ap.add_argument("--list-checks", action="store_true",
                    help="list the checks and their profiles, then exit")
    args = ap.parse_args(argv)

    if args.list_checks:
        for profile in (STRICT, REFERENCE):
            print(f"{profile}:")
            for c in CHECKS:
                if c["profile"] == profile:
                    print(f"  {c['name']:<26} {c['description']}")
        return 0
    if not args.files:
        ap.error("no input files (use - for stdin)")

    user_known = parse_known(args.known)
    for path in args.known_file:
        user_known |= read_known_file(path)
    ctx = {
        "user_known": user_known,
        "known": user_known | (set() if args.no_builtin_known else BUILTIN_KNOWN),
        "source_values": source_values(read_source(p) for p in
                                       iter_source_files(args.source)),
    }
    active = [c for c in CHECKS if args.profile == REFERENCE or c["profile"] == STRICT]

    out = sys.stdout
    out.write(f"technical-writing checks, profile: {args.profile}\n")
    for path in args.files:
        doc = Document("<stdin>" if path == "-" else path, read_text(path))
        not_run = []
        banner_shown = False
        for c in active:
            if c["needs"] == "source" and not args.source:
                not_run.append(c["name"])
                continue
            findings = sorted(c["func"](doc, ctx), key=lambda f: f.offset)
            if not findings:
                continue
            if c["profile"] == REFERENCE and not banner_shown:
                out.write("\n== Reference only ==\n" + REFERENCE_BANNER + "\n")
                banner_shown = True
            out.write(f"\n-- {c['name']}: {c['description']}\n")
            limit = args.max_per_check or len(findings)
            for f in findings[:limit]:
                out.write(f"{doc.name}:{doc.line_of(f.offset)}: {f.message}\n")
                out.write(f"    {doc.snippet(f.offset)}\n")
            if len(findings) > limit:
                out.write(f"    ... {len(findings) - limit} more not shown "
                          f"(--max-per-check 0 shows all)\n")
        if not_run:
            out.write(f"\nNot run on {doc.name}: {', '.join(not_run)} "
                      f"(pass the author's material with --source)\n")
    out.write("\n" + NOT_CHECKED + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # The reader (for example head) closed the pipe early.
        sys.stderr.close()
        sys.exit(0)
