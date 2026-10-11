"""Rates per 1,000 words of the claim families cited in the technical-writing skill.

Usage: python3 claim_families.py   (needs build/human_docs.json and data/llm_corpus/; writes results/claim_families.json)
"""
import json, pathlib, re

from prep_human import md_prose

HERE = pathlib.Path(__file__).resolve().parent
FAMILIES = {
    'universal claims': r"\b(every|always|never|nothing|cannot|can't|already)\b",
    'compatibility reassurance': r"\b(unaffected|unchanged|keeps? working|continues? to work|(existing|current) (code|programs?|users?|behaviou?r) (is|are|keeps?|continues?|remains?)\b|not affected|no existing code)",
    'cost assertions': r"\b(the|a|its|this|that|no|extra|small) (cost|costs|overhead)\b|\bcosts? (is|are|one|a|nothing|only)\b",
    'silent/deliberate': r"\b(silently|deliberately|intentionally)\b",
}


def rate(texts, rx):
    n = sum(len(t.split()) for t in texts)
    return round(sum(len(re.findall(rx, t, re.I)) for t in texts) / n * 1000, 3)


def main():
    prompts = {x['id'] for x in json.load(open(HERE / 'data/prompts.json'))}
    human = [d for d in json.load(open(HERE / 'build/human_docs.json')) if len(d['text'].split()) >= 300]
    sets = {m: [md_prose(f.read_text()) for f in sorted((HERE / 'data/llm_corpus' / m).glob('*.md'))] for m in ('opus', 'sonnet', 'haiku')}
    sets['human, same topics'] = [d['text'] for d in human if d['name'] in prompts]
    sets['human, 2018-2021'] = [d['text'] for d in human if d['year'] >= 2018]
    sets['human, all'] = [d['text'] for d in human]
    out = {fam: {name: rate(texts, rx) for name, texts in sets.items()} for fam, rx in FAMILIES.items()}
    (HERE / 'results').mkdir(exist_ok=True)
    json.dump(out, open(HERE / 'results/claim_families.json', 'w'), indent=1)
    names = list(sets)
    print(f"{'per 1k words':28s}" + ''.join(f'{n:>20s}' for n in names))
    for fam, row in out.items():
        print(f'{fam:28s}' + ''.join(f'{row[n]:20.3f}' for n in names))


if __name__ == '__main__':
    main()
