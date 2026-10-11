"""Count bad patterns in the 40 test topics: no-skill vs skill documents vs human originals.

Usage: python3 known_patterns.py   (needs node for the EQ-Bench contrast detector; writes results/known_patterns.json)
Text inside [TODO: ...] markers is removed first. Rates are per 1,000 words, except where noted.
"""
import json, pathlib, re, subprocess, tempfile

from compare_skill import CORPORA
from prep_human import md_prose

HERE = pathlib.Path(__file__).resolve().parent
MODELS = ('opus', 'sonnet', 'haiku')
TODO = re.compile(r'\[TODO:[^\]]*\]', re.I)
PATTERNS = {
    # Patterns surfaced by surface_patterns.py in the skill documents
    'skill vocabulary in the prose': r"\bthe force (behind|is|that|here)\b|\bdeciding reason\b|\bcosts? accepted\b|\bexpensive to reverse\b|\bcentral (tension|trade-?off|question)\b|\bdisagreement test\b|\bsuggestions? for the author\b|\bfor the author to (evaluate|confirm|decide)\b",
    'review notes in the prose': r"\bthe abstract (says|states|does not|doesn't|gives|names|mentions|describes|calls)\b|\b(the|author's|supplied|this) material\b|\bnot (stated|supplied|given|described) in\b|\bthe author (must|should|has not|did not|needs|would)\b|\bneeds evidence\b|\bthis is a (compatibility|cost|universal) claim\b",
    # The skill's own scan list
    'stock significance': r"\b(pivotal|crucial|plays? a key role|underscores?|landscape|realm|testament)\b",
    'stock vocabulary': r"\b(delve|leverag(e|es|ed|ing)|utili[sz](e|es|ed|ing)|enhanc(e|es|ed|ing)|subsequently|robust|seamless(ly)?|harness|unlock|showcase|nuanced|intricate)\b",
    'design-doc buzzwords': r"\b(scalable|flexible|extensible|maintainable|future-?proof|best practices)\b",
    'avoided is/has': r"\b(serves as|stands as|boasts)\b",
    'vague relations': r"\b(associated with|in connection with|linked to)\b",
    'worth noting / importantly / notably / interestingly': r"\b(it is worth noting|worth noting|importantly|notably|interestingly)\b",
    'em dashes': r"—| -- ",
    'bold-label bullets (per 100 lines)': None,
    'headings (per 1k words)': None,
    'EQ-Bench not-x-but-y (per 1k chars)': None,
}


def load_sets():
    prompts = {p['id']: p for p in json.load(open(HERE / 'data/prompts.json'))}
    test_ids = [i for i, p in prompts.items() if p['split'] == 'test']
    human = {d['name']: d['text'] for d in json.load(open(HERE / 'build/human_docs.json'))}
    raw_orig = {}
    for i in test_ids:   # human originals with markup, for typography counts
        p = HERE / 'sources/peps/peps' / f'{i}.rst'
        raw_orig[i] = p.read_text(errors='replace') if p.exists() else (HERE / 'sources/rfcs/text' / f'{i}.md').read_text(errors='replace')
    sets = {}
    for m in MODELS:
        for corpus, label in CORPORA:
            if not all((HERE / 'data' / corpus / m / f'{i}.md').exists() for i in test_ids):
                continue
            raws = [TODO.sub(' ', (HERE / 'data' / corpus / m / f'{i}.md').read_text(errors='replace')) for i in test_ids]
            sets[f'{m}, {label}'] = (raws, [md_prose(r) for r in raws])
    sets['human originals'] = ([raw_orig[i] for i in test_ids], [human[i] for i in test_ids])
    return sets


def main():
    out = {}
    for name, (raws, prose) in load_sets().items():
        words = sum(len(t.split()) for t in prose)
        row = {}
        for k, rx in PATTERNS.items():
            if rx:
                row[k] = round(sum(len(re.findall(rx, t, re.I)) for t in prose) / words * 1000, 3)
        lines = [l for r in raws for l in r.splitlines() if l.strip()]
        row['bold-label bullets (per 100 lines)'] = round(sum(bool(re.match(r'\s*([-*]|\d+\.)\s+\*\*[^*]+\*\*[:.]?', l)) for l in lines) / len(lines) * 100, 2)
        md_heads = sum(bool(re.match(r'#{1,6}\s', l)) for l in lines)
        rst_heads = sum(1 for r in raws for a, b in zip(r.splitlines(), r.splitlines()[1:]) if a.strip() and re.fullmatch(r'[=\-~^]{3,}', b.strip()))
        row['headings (per 1k words)'] = round((md_heads + rst_heads) / words * 1000, 2)
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump(prose, f)
        counts = json.loads(subprocess.run(['node', str(HERE / 'contrast_counts.mjs'), f.name], capture_output=True, text=True, check=True).stdout)
        row['EQ-Bench not-x-but-y (per 1k chars)'] = round(sum(counts) / sum(len(t) for t in prose) * 1000, 3)
        out[name] = row
    (HERE / 'results').mkdir(exist_ok=True)
    json.dump(out, open(HERE / 'results/known_patterns.json', 'w'), indent=1)
    names = list(out)
    print(f"{'':42s}" + ''.join(f'{n[:19]:>20s}' for n in names))
    for k in PATTERNS:
        print(f'{k[:42]:42s}' + ''.join(f'{out[n][k]:20.3f}' for n in names))


if __name__ == '__main__':
    main()
