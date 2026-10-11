"""Format adapters for check.py.

An adapter finds the parts of a document that are not prose (code, math,
comments, markup commands) and the bookkeeping that markup makes exact
(labels, references, citation keys). It never changes offsets, so findings
from any view map back to the right line of the original file.

The checks in check.py work on the resulting Structure and do not know which
format it came from. Files in other formats get no Structure, and the
structural checks are reported as not run.
"""

import os
import re

# Placeholders that replace a span in the prose view. They are not letters,
# so word counts and word patterns skip them.
INLINE_MATH = "\ue000"
DISPLAY_MATH = "\ue002"
INLINE_CODE = "\ue001"

EXTENSIONS = {
    ".tex": "latex", ".ltx": "latex", ".latex": "latex",
    ".md": "markdown", ".markdown": "markdown", ".mdown": "markdown",
    ".qmd": "markdown", ".rmd": "markdown",
}

FLOAT_KINDS = ("figure", "table", "listing", "algorithm")


def detect_format(path, override="auto"):
    if override != "auto":
        return override
    if path == "-":
        return "text"
    return EXTENSIONS.get(os.path.splitext(path)[1].lower(), "text")


class MathSpan:
    def __init__(self, start, end, body_start, body_end, display, numbered=False):
        self.start, self.end = start, end
        self.body_start, self.body_end = body_start, body_end
        self.display = display
        self.numbered = numbered


class Structure:
    def __init__(self, fmt):
        self.format = fmt
        self.math = []          # MathSpan
        self.code_blocks = []   # (start, end)
        self.code_inline = []   # (start, end)
        self.comments = []      # (start, end)
        self.hidden = []        # (start, end): markup that is neither prose nor math
        self.labels = []        # (key, kind, offset)
        self.refs = []          # (key, offset)
        self.citations = []     # (key, offset)
        self.unlabeled_numbered = []  # offsets of numbered equations with no label
        self.unlabeled_floats = []    # (kind, offset) of floats with no label
        # Regions that are not prose but were left unclaimed so that citations
        # and references inside them are still recorded.
        self.tables = []        # (start, end): blanked in prose, digits kept
        self.pseudocode = []    # (start, end): blanked in both views
        self.preamble = None    # (start, end) of a LaTeX preamble
        self.macros = {}        # LaTeX macros: name -> (number of arguments, body)

    def in_comment(self, offset):
        return any(a <= offset < b for a, b in self.comments)

    def views(self, text):
        """Return (prose, numbers) views of text, both the same length.

        The prose view blanks markup, code and comments, and replaces each
        formula and each inline code span with a placeholder character. The
        numbers view is the same except that formulas keep their digits.
        """
        prose = list(text)
        blank(prose, self.hidden + self.code_blocks + self.comments)
        numbers = prose[:]
        for a, b in self.code_inline:
            blank(prose, [(a, b)])
            prose[a] = INLINE_CODE
            blank(numbers, [(a, b)])
        for m in self.math:
            blank(prose, [(m.start, m.end)])
            prose[m.start] = DISPLAY_MATH if m.display else INLINE_MATH
            body = text[m.body_start:m.body_end]
            for c in re.finditer(r"\\[A-Za-z]+|[{}_^$]", body):
                blank(numbers, [(m.body_start + c.start(), m.body_start + c.end())])
        blank(prose, self.tables + self.pseudocode)
        blank(numbers, self.pseudocode)
        for a, b in self.tables:
            for c in re.finditer(r"\\[A-Za-z]+|[$&{}_^]", text[a:b]):
                blank(numbers, [(a + c.start(), a + c.end())])
        return "".join(prose), "".join(numbers)

    def finish(self):
        """Drop formulas inside tables and pseudocode: they are not running text."""
        regions = self.tables + self.pseudocode
        self.math = [m for m in self.math
                     if not any(a <= m.start < b for a, b in regions)]
        return self


def blank(chars, spans):
    for a, b in spans:
        for i in range(a, b):
            if not chars[i].isspace():
                chars[i] = " "


class Scanner:
    """Text in which claimed spans are blanked, so later patterns skip them."""

    def __init__(self, text):
        self.chars = list(text)
        self._view = text

    def claim(self, a, b):
        blank(self.chars, [(a, b)])
        self._view = None

    @property
    def view(self):
        if self._view is None:
            self._view = "".join(self.chars)
        return self._view


def brace_end(text, i):
    """Return the index after the brace group starting at text[i] == "{"."""
    depth = 0
    j = i
    while j < len(text):
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return len(text)


def keys_of(arg):
    return [k.strip() for k in arg.split(",") if k.strip() and k.strip() != "*"]


def label_kind(key, offset, floats):
    for kind, a, b in floats:
        if a <= offset < b:
            return kind
    prefix = re.match(r"([A-Za-z]+)[:\-_]", key)
    prefix = prefix.group(1).lower() if prefix else ""
    return {"fig": "figure", "figure": "figure", "tab": "table", "tbl": "table",
            "table": "table", "eq": "equation", "eqn": "equation",
            "lst": "listing", "alg": "algorithm"}.get(prefix, "other")


# ---------------------------------------------------------------------------
# LaTeX

MATH_ENVS = ("equation|align|gather|multline|eqnarray|flalign|alignat|"
             "displaymath|math|dmath")
NUMBERED_ENVS = {"equation", "align", "gather", "multline", "eqnarray", "flalign",
                 "alignat", "dmath"}
LATEX_MATH_ENV_RE = re.compile(
    r"\\begin\{(" + MATH_ENVS + r")(\*?)\}(?:\{[^}]*\})?(.*?)\\end\{\1\2\}", re.S)
LATEX_FLOAT_RE = re.compile(
    r"\\begin\{(figure|table|subfigure|subtable|wrapfigure|wraptable|"
    r"sidewaysfigure|sidewaystable|algorithm|listing)(\*?)\}(.*?)\\end\{\1\2\}", re.S)
CITE_CMDS = re.compile(
    r"(?:[Cc]ite\w*|[a-z]*cite[a-z]*|nocite|citep|citet|citealp|citealt|"
    r"citeauthor|citeyear|parencite|textcite|autocite|footcite|smartcite)$")
REF_CMDS = {"ref", "eqref", "autoref", "cref", "Cref", "pageref", "vref", "nameref",
            "labelcref", "cpageref", "Autoref", "subref", "crefrange"}
# Commands whose brace arguments are keys, paths or lengths, not prose:
# name -> number of brace arguments to hide.
KEYED_CMDS = {
    "label": 1, "includegraphics": 1, "input": 1, "include": 1,
    "bibliography": 1, "bibliographystyle": 1, "addbibresource": 1,
    "usepackage": 1, "RequirePackage": 1, "documentclass": 1, "url": 1,
    "vspace": 1, "hspace": 1, "setlength": 2, "addtolength": 2, "setcounter": 2,
    "newcommand": 2, "renewcommand": 2, "providecommand": 2, "DeclareMathOperator": 2,
    "newenvironment": 3, "renewenvironment": 3, "newtheorem": 2, "hypersetup": 1,
    "graphicspath": 1, "pagestyle": 1, "thispagestyle": 1, "multicolumn": 2,
    "multirow": 2, "cline": 1, "cmidrule": 1, "end": 1, "href": 1, "color": 1,
    "textcolor": 1, "definecolor": 3, "resizebox": 2, "scalebox": 1, "rule": 2,
    "fontsize": 2, "linespread": 1, "geometry": 1, "captionsetup": 1,
}
TABULAR_ENVS = {"tabular": 1, "array": 1, "tabularx": 2, "tabular*": 2, "tabulary": 2,
                "longtable": 1, "minipage": 1, "wrapfigure": 2, "subfigure": 1,
                "subtable": 1}


def analyze_latex(text):
    s = Structure("latex")
    sc = Scanner(text)

    for m in re.finditer(r"\\begin\{(verbatim|Verbatim|lstlisting|minted|alltt)(\*?)\}"
                         r".*?\\end\{\1\2\}", sc.view, re.S):
        s.code_blocks.append(m.span())
        sc.claim(*m.span())
    for m in re.finditer(r"\\begin\{comment\}.*?\\end\{comment\}", sc.view, re.S):
        s.comments.append(m.span())
        sc.claim(*m.span())
    for m in re.finditer(r"\\(?:verb|lstinline)\*?([^\sA-Za-z{\[])(.*?)\1"
                         r"|\\lstinline(?:\[[^\]]*\])?\{[^}]*\}|\\texttt\{[^{}]*\}",
                         sc.view):
        s.code_inline.append(m.span())
        sc.claim(*m.span())
    for m in re.finditer(r"(?<!\\)%[^\n]*", sc.view):
        s.comments.append(m.span())
        sc.claim(*m.span())
    begin = re.search(r"\\begin\{document\}", sc.view)
    if begin:
        s.preamble = (0, begin.end())
        s.hidden.append((0, begin.end()))
        sc.claim(0, begin.end())
        end = re.search(r"\\end\{document\}", sc.view)
        if end:
            s.hidden.append((end.start(), len(text)))
            sc.claim(end.start(), len(text))

    for m in re.finditer(r"\\begin\{(tabular\*?|tabularx|tabulary|longtable)\}.*?"
                         r"\\end\{\1\}", sc.view, re.S):
        s.tables.append(m.span())
    for m in re.finditer(r"\\begin\{(algorithmic\*?|algpseudocode|tikzpicture)\}.*?"
                         r"\\end\{\1\}", sc.view, re.S):
        s.pseudocode.append(m.span())
    for m in re.finditer(r"\\(?:(?:re|provide)?newcommand\*?\s*\{?\\([A-Za-z]+)\}?"
                         r"\s*(?:\[(\d)\])?\s*(?:\[[^\]]*\])?"
                         r"|def\s*\\([A-Za-z]+)((?:#\d)*))\s*(?=\{)", text):
        e = brace_end(text, m.end())
        nargs = int(m.group(2) or 0) if m.group(1) else len(m.group(4)) // 2
        s.macros[m.group(1) or m.group(3)] = (nargs, text[m.end() + 1:e - 1])

    floats = []
    for m in LATEX_FLOAT_RE.finditer(sc.view):
        kind = m.group(1).replace("sideways", "").replace("wrap", "").replace("sub", "")
        floats.append((kind, m.start(), m.end()))
        if not re.search(r"\\label\{", m.group(3)) and m.group(1).startswith(
                ("figure", "table", "algorithm", "listing")):
            if re.search(r"\\caption", m.group(3)):
                s.unlabeled_floats.append((kind, m.start()))

    for m in LATEX_MATH_ENV_RE.finditer(sc.view):
        numbered = m.group(1) in NUMBERED_ENVS and not m.group(2)
        add_latex_math(s, sc, text, m.start(), m.end(), m.start(3), m.end(3), True, numbered)
    for rx, display in ((r"\$\$(.+?)\$\$", True), (r"\\\[(.+?)\\\]", True),
                        (r"\\\((.+?)\\\)", False),
                        (r"(?<!\\)\$((?:\\.|[^$\\])+?)\$", False)):
        for m in re.finditer(rx, sc.view, re.S):
            add_latex_math(s, sc, text, m.start(), m.end(), m.start(1), m.end(1),
                           display, False)

    view = sc.view
    i = 0
    for m in re.finditer(r"\\([A-Za-z@]+\*?)|\\\\(?:\[[^\]]*\])?|\\[^A-Za-z]|[{}~]", view):
        if m.start() < i:
            continue
        name = m.group(1)
        if name is None:
            if m.group(0).startswith("\\") and len(m.group(0)) == 2 and m.group(0) != "\\\\":
                s.hidden.append((m.start(), m.start() + 1))  # keep "%" of "\%"
            else:
                s.hidden.append(m.span())
            continue
        bare = name.rstrip("*")
        j = m.end()
        if bare == "begin":
            j, arg = take_args(view, j, 1)
            env = arg[0] if arg else ""
            j, _ = take_args(view, j, TABULAR_ENVS.get(env, 0))
            s.hidden.append((m.start(), j))
            i = j
        elif CITE_CMDS.match(bare) or bare in REF_CMDS or bare in KEYED_CMDS:
            n = 1 if (CITE_CMDS.match(bare) or bare in REF_CMDS) else KEYED_CMDS[bare]
            j, args = take_args(view, j, n)
            if args:
                if CITE_CMDS.match(bare):
                    s.citations.extend((k, m.start()) for k in keys_of(args[0]))
                elif bare in REF_CMDS:
                    s.refs.extend((k, m.start()) for k in keys_of(args[0]))
                elif bare == "label":
                    key = args[0].strip()
                    s.labels.append((key, label_kind(key, m.start(), floats), m.start()))
            s.hidden.append((m.start(), j))
            i = j
        else:
            s.hidden.append(m.span())
    return s.finish()


def take_args(view, j, n):
    """Skip optional [..] groups and n brace groups from view[j]."""
    args = []
    while True:
        k = j
        while k < len(view) and view[k] in " \t\n":
            k += 1
        if k < len(view) and view[k] == "[" and len(args) < n:
            close = view.find("]", k)
            if close == -1:
                break
            j = close + 1
            continue
        if k < len(view) and view[k] == "{" and len(args) < n:
            e = brace_end(view, k)
            args.append(view[k + 1:e - 1])
            j = e
            continue
        break
    return j, args


def add_latex_math(s, sc, text, start, end, body_start, body_end, display, numbered):
    body = text[body_start:body_end]
    labels = list(re.finditer(r"\\label\{([^}]*)\}", body))
    for lm in labels:
        s.labels.append((lm.group(1).strip(), "equation", body_start + lm.start()))
    for rm in re.finditer(r"\\(?:eq)?ref\{([^}]*)\}", body):
        s.refs.extend((k, body_start + rm.start()) for k in keys_of(rm.group(1)))
    if numbered and not labels:
        rows = [r for r in re.split(r"\\\\", body) if r.strip()]
        if not rows or not all(re.search(r"\\(?:nonumber|notag)\b", r) for r in rows):
            s.unlabeled_numbered.append(start)
    s.math.append(MathSpan(start, end, body_start, body_end, display, numbered))
    sc.claim(start, end)


# ---------------------------------------------------------------------------
# Markdown (CommonMark, with pandoc and Quarto conventions for math,
# citations and cross-reference labels)

CROSSREF = r"(?:fig|tbl|eq|lst|sec)[:\-]"
MD_KEY = r"[A-Za-z0-9_][\w:.#$%&\-+?<>~/]*\w|[A-Za-z0-9_]"


def analyze_markdown(text):
    s = Structure("markdown")
    sc = Scanner(text)

    fm = re.match(r"---[ \t]*\n.*?\n(?:---|\.\.\.)[ \t]*(?:\n|$)", text, re.S)
    if fm:
        s.hidden.append(fm.span())
        sc.claim(*fm.span())
    for m in re.finditer(r"(?ms)^[ \t]*(`{3,}|~{3,})([^\n]*)\n(.*?)(?:^[ \t]*\1[`~]*[ \t]*$|\Z)",
                         sc.view):
        if m.group(2).strip().lower().lstrip("{.").startswith("math"):
            s.math.append(MathSpan(m.start(), m.end(), m.start(3), m.end(3), True))
        else:
            s.code_blocks.append(m.span())
        sc.claim(*m.span())
    for m in re.finditer(r"<!--.*?-->", sc.view, re.S):
        s.comments.append(m.span())
        sc.claim(*m.span())
    for m in re.finditer(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)", sc.view, re.S):
        s.code_inline.append(m.span())
        sc.claim(*m.span())

    for m in LATEX_MATH_ENV_RE.finditer(sc.view):
        numbered = m.group(1) in NUMBERED_ENVS and not m.group(2)
        add_latex_math(s, sc, text, m.start(), m.end(), m.start(3), m.end(3), True, numbered)
    for rx, display in ((r"\$\$(.+?)\$\$", True), (r"\\\[(.+?)\\\]", True),
                        (r"\\\((.+?)\\\)", False),
                        (r"(?<![\\$\w])\$(?![\s$])((?:\\.|[^$\\\n])+?)(?<![\s\\])\$(?!\d)",
                         False)):
        for m in re.finditer(rx, sc.view, re.S):
            span = MathSpan(m.start(), m.end(), m.start(1), m.end(1), display)
            s.math.append(span)
            sc.claim(m.start(), m.end())

    for m in re.finditer(r"\{#(" + CROSSREF + r"[\w:.\-]+)[^}\n]*\}", sc.view):
        key = m.group(1)
        s.labels.append((key, label_kind(key, m.start(), []), m.start()))
        s.hidden.append(m.span())
        sc.claim(*m.span())

    bracketed = list(re.finditer(r"\[[^\[\]\n]*@[^\[\]\n]*\]", sc.view))
    for m in bracketed:
        found = False
        for k in re.finditer(r"(?<![\w.])-?@(" + MD_KEY + r")", m.group(0)):
            found = True
            key = k.group(1)
            if re.match(CROSSREF, key):
                s.refs.append((key, m.start() + k.start()))
            else:
                s.citations.append((key, m.start() + k.start()))
        if found:
            s.hidden.append(m.span())
            sc.claim(*m.span())
    has_citations = bool(s.citations)
    for m in re.finditer(r"(?<![\w.@\[])@(" + MD_KEY + r")", sc.view):
        key = m.group(1)
        if re.match(CROSSREF, key):
            s.refs.append((key, m.start()))
        elif has_citations:
            s.citations.append((key, m.start()))
        else:
            continue
        s.hidden.append(m.span())

    separator = re.compile(r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$")
    for m in re.finditer(r"(?m)(?:^[^\n]*\|[^\n]*(?:\n|$)){2,}", sc.view):
        if any(separator.match(line) for line in m.group(0).splitlines()):
            s.tables.append(m.span())

    for rx in (r"\[([^\]\n]+)\]\(\1\)",  # a link whose text is its own target
               r"\]\([^)\s]*(?:\s+\"[^\"]*\")?\)", r"<https?://[^>\s]+>",
               r"(?m)^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*\S.*$", r"</?[A-Za-z][^>\n]*>"):
        for m in re.finditer(rx, sc.view):
            s.hidden.append(m.span())
            sc.claim(*m.span())
    return s.finish()


ANALYZERS = {"latex": analyze_latex, "markdown": analyze_markdown}


def analyze(text, fmt):
    """Return a Structure for text in format fmt, or None for plain text."""
    fn = ANALYZERS.get(fmt)
    return fn(text) if fn else None
