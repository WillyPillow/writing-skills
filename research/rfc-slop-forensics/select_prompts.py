"""Pick 120 topics (60 PEPs, 60 Rust RFCs) and write the generation prompts.

Usage: python3 select_prompts.py   (needs build/human_docs.json; writes data/prompts.json and data/batches/)
A topic qualifies if its document is 1,000-6,000 words of prose and has an abstract (PEPs: Standards
Track with an Abstract section; RFCs: a Summary section and a feature name). Every third topic is held out
for testing, giving 80 train and 40 test topics.
"""
import json, pathlib, random, re

HERE = pathlib.Path(__file__).resolve().parent
SEED = 20261011


def section(text, names, md):
    if md:
        m = re.search(r'^#+\s*(?:' + names + r')\b.*?\n(.*?)(?=^#+\s)', text, re.M | re.S | re.I)
    else:
        m = re.search(r'^(?:' + names + r')\s*\n[=\-~^]{3,}\s*\n(.*?)(?=^\S[^\n]*\n[=\-~^]{3,}\s*$)', text, re.M | re.S | re.I)
    if not m:
        return None
    s = m.group(1)
    s = re.sub(r'^\[[^\]]+\]:.*$', '', s, flags=re.M)          # md link refs
    s = re.sub(r'```.*?```', '', s, flags=re.S)
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'\s+', ' ', s).strip()
    words = s.split()
    return ' '.join(words[:130]) + (' ...' if len(words) > 130 else '') if len(words) >= 25 else None


def main():
    docs = {d['name']: d for d in json.load(open(HERE / 'build/human_docs.json'))}
    cands = {'pep': [], 'rust-rfc': []}
    for p in sorted((HERE / 'sources/peps/peps').glob('pep-*.rst')):
        if p.stem not in docs:
            continue
        t = p.read_text(errors='replace')
        if not re.search(r'^Type:\s*Standards Track', t, re.M):
            continue
        title = re.search(r'^Title:\s*(.+)$', t, re.M).group(1).strip()
        ab = section(t, 'Abstract', md=False)
        n = len(docs[p.stem]['text'].split())
        if ab and 1000 <= n <= 6000:
            cands['pep'].append({'id': p.stem, 'corpus': 'pep', 'title': f"PEP {int(p.stem[4:])}: {title}", 'abstract': ab, 'words': n})
    for p in sorted((HERE / 'sources/rfcs/text').glob('*.md')):
        if p.stem not in docs:
            continue
        t = p.read_text(errors='replace')
        fn = re.search(r'Feature Name:\s*`?([^`\n]+)`?', t)
        ab = section(t, 'Summary', md=True)
        n = len(docs[p.stem]['text'].split())
        if ab and fn and 1000 <= n <= 6000:
            num = int(p.stem.split('-')[0])
            cands['rust-rfc'].append({'id': p.stem, 'corpus': 'rust-rfc', 'title': f"Rust RFC {num}: {fn.group(1).strip()}", 'abstract': ab, 'words': n})
    print('candidates:', {k: len(v) for k, v in cands.items()})
    rng = random.Random(SEED)
    chosen = rng.sample(cands['pep'], 60) + rng.sample(cands['rust-rfc'], 60)
    rng.shuffle(chosen)
    for i, c in enumerate(chosen):
        c['split'] = 'test' if i % 3 == 2 else 'train'
    (HERE / 'data').mkdir(exist_ok=True)
    json.dump(chosen, open(HERE / 'data/prompts.json', 'w'), indent=1)

    # 12 batches of 10 topics; each generation agent receives one batch file.
    bdir = HERE / 'data/batches'
    bdir.mkdir(exist_ok=True)
    for b in range(12):
        with open(bdir / f'batch_{b:02d}.md', 'w') as f:
            for x in chosen[b * 10:(b + 1) * 10]:
                kind = 'Python Enhancement Proposal (PEP)' if x['corpus'] == 'pep' else 'Rust language/tooling RFC'
                f.write(f"## id: {x['id']}\nDocument type: {kind}\nTitle: {x['title']}\nAbstract: {x['abstract']}\n\n")
    print(sum(c['split'] == 'train' for c in chosen), 'train,', sum(c['split'] == 'test' for c in chosen), 'test')


if __name__ == '__main__':
    main()
