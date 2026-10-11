"""Extract prose from PEPs and Rust RFCs started in 2021 or earlier.

Usage: python3 prep_human.py   (writes build/human_docs.json)
Code blocks, inline code, URLs and metadata headers are removed, so only prose is compared.
"""
import json, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
MAX_YEAR = 2021


def clean_inline(s):
    s = re.sub(r'``[^`]*``|`[^`]*`', ' ', s)              # inline code / rst roles
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)        # md links -> text
    s = re.sub(r'https?://\S+', ' ', s)
    s = re.sub(r':[a-z]+:', ' ', s)                       # rst role prefixes
    return s


def md_prose(text):
    out, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            in_fence = not in_fence; continue
        if in_fence or line.startswith(('    ', '\t')) or line.startswith('[') and ']: ' in line:
            continue
        if line.startswith('- ') and re.match(r'- (Feature Name|Start Date|RFC PR|Rust Issue)', line):
            continue
        out.append(clean_inline(line))
    return '\n'.join(out)


def rst_prose(text):
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip():   # header block
        i += 1
    out, skipping = [], False
    for line in lines[i:]:
        stripped = line.strip()
        if skipping:
            if not stripped or line[:1] in ' \t':
                continue
            skipping = False
        if stripped.startswith('..') or stripped.endswith('::'):
            # directive or literal-block intro: drop the indented block that follows
            skipping = True
            if stripped.endswith('::') and not stripped.startswith('..'):
                out.append(clean_inline(line[:-1]))
            continue
        if re.fullmatch(r'[=\-~^*#+`]{3,}', stripped):     # section underline
            continue
        if stripped.startswith('>>>') or stripped.startswith('|'):
            continue
        out.append(clean_inline(line))
    return '\n'.join(out)


def main():
    peps_dir, rfcs_dir = HERE / 'sources/peps/peps', HERE / 'sources/rfcs/text'
    docs = []
    for p in sorted(peps_dir.glob('pep-*.rst')):
        t = p.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'^Created:\s*.*?(\d{4})', t, re.M)
        if not m or int(m.group(1)) > MAX_YEAR:
            continue
        docs.append({'corpus': 'pep', 'name': p.stem, 'year': int(m.group(1)), 'text': rst_prose(t)})
    for p in sorted(rfcs_dir.glob('*.md')):
        t = p.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'Start Date:\s*(\d{4})', t)
        if not m or int(m.group(1)) > MAX_YEAR:
            continue
        docs.append({'corpus': 'rust-rfc', 'name': p.stem, 'year': int(m.group(1)), 'text': md_prose(t)})
    (HERE / 'build').mkdir(exist_ok=True)
    json.dump(docs, open(HERE / 'build/human_docs.json', 'w'))
    for c in ('pep', 'rust-rfc'):
        ds = [d for d in docs if d['corpus'] == c]
        print(c, len(ds), 'docs,', sum(len(d['text'].split()) for d in ds), 'words')


if __name__ == '__main__':
    main()
