"""Compare documents written with the technical-writing skill against those written without it, on the 40 test topics.

Usage: python3 compare_skill.py   (needs build/, data/llm_corpus/, data/llm_corpus_skill/ and results/forensics.json;
writes results/skill_comparison.json)
[TODO: ...] markers are counted, then removed before scoring, since they record open questions rather than claims.
"""
import json, pathlib, random, re
import statistics as st

from analyze import TEMPLATE, TOPIC, auc, content_tokens, score, units
from claim_families import FAMILIES
from prep_human import md_prose

HERE = pathlib.Path(__file__).resolve().parent
MODELS = ('opus', 'sonnet', 'haiku')
TODO = re.compile(r'\[TODO:[^\]]*\]', re.I)


def rate(texts, rx):
    n = sum(len(t.split()) for t in texts)
    return round(sum(len(re.findall(rx, t, re.I)) for t in texts) / n * 1000, 3)


def main():
    prompts = {p['id']: p for p in json.load(open(HERE / 'data/prompts.json'))}
    test_ids = [i for i, p in prompts.items() if p['split'] == 'test']
    human_all = {d['name']: d for d in json.load(open(HERE / 'build/human_docs.json')) if len(d['text'].split()) >= 300}
    others = sorted(set(human_all) - set(prompts))
    extra_test = random.Random(7).sample(others, 160)          # same held-out set as analyze.py
    rows = json.load(open(HERE / 'results/forensics.json'))['rows']
    register = [r['unit'] for r in rows if r['unit'] not in TEMPLATE | TOPIC]

    def load(corpus, m):
        out = []
        for i in test_ids:
            p = HERE / 'data' / corpus / m / f'{i}.md'
            if p.exists():
                raw = md_prose(p.read_text(errors='replace'))
                out.append({'id': i, 'todos': len(TODO.findall(raw)), 'text': TODO.sub(' ', raw)})
        return out

    human = [human_all[i]['text'] for i in test_ids + extra_test]
    h_scores = [score(units(content_tokens(t)), register) for t in human]
    report = {'register_terms': len(register),
              'human_register_hits_median': round(st.median(h_scores), 1)}
    for m in MODELS:
        for corpus, label in (('llm_corpus', 'without skill'), ('llm_corpus_skill', 'with skill')):
            docs = load(corpus, m)
            if not docs:
                continue
            sc = [score(units(content_tokens(d['text'])), register) for d in docs]
            report[f'{m}, {label}'] = {
                'docs': len(docs),
                'median_words': int(st.median(len(d['text'].split()) for d in docs)),
                'todo_markers_per_doc': round(sum(d['todos'] for d in docs) / len(docs), 1),
                'register_hits_median': round(st.median(sc), 1),
                'auc_vs_human': round(auc(sc, h_scores), 3),
                'claims_per_1k_words': {f: rate([d['text'] for d in docs], rx) for f, rx in FAMILIES.items()},
            }
    report['human (40 test originals), claims_per_1k_words'] = {f: rate([human_all[i]['text'] for i in test_ids], rx) for f, rx in FAMILIES.items()}
    (HERE / 'results').mkdir(exist_ok=True)
    json.dump(report, open(HERE / 'results/skill_comparison.json', 'w'), indent=1)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
