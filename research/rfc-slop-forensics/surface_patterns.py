"""Find terms the skill-written documents over-use, on the 40 test topics.

Usage: python3 surface_patterns.py   (writes results/skill_surface_terms.json)
Compares the 120 skill documents (TODO text removed) against (a) the 40 human originals plus the human
baseline used by analyze.py, and (b) the 120 no-skill documents on the same topics. Same filters as analyze.py,
scaled to the smaller corpus: a term must appear in >= 6 documents, >= 4 topics and >= 2 models.
"""
import json, pathlib, random, re
from collections import Counter, defaultdict

from analyze import agg, content_tokens, contexts, log_odds_z, ngram_n, units
from prep_human import md_prose

HERE = pathlib.Path(__file__).resolve().parent
MODELS = ('opus', 'sonnet', 'haiku')
TODO = re.compile(r'\[TODO:[^\]]*\]', re.I)


def main():
    prompts = {p['id']: p for p in json.load(open(HERE / 'data/prompts.json'))}
    test_ids = [i for i, p in prompts.items() if p['split'] == 'test']
    human_all = {d['name']: d for d in json.load(open(HERE / 'build/human_docs.json')) if len(d['text'].split()) >= 300}
    others = sorted(set(human_all) - set(prompts))
    extra_test = random.Random(7).sample(others, 160)
    base_ids = [i for i in human_all if i not in set(extra_test)]      # test originals now count as baseline

    def load(corpus):
        out = []
        for m in MODELS:
            for i in test_ids:
                raw = (HERE / 'data' / corpus / m / f'{i}.md').read_text(errors='replace')
                out.append({'model': m, 'id': i, 'raw': raw, 'toks': content_tokens(TODO.sub(' ', md_prose(raw)))})
        return out
    skill, plain = load('llm_corpus_skill'), load('llm_corpus')
    cS, dfS, nS = agg([d['toks'] for d in skill])
    cN, _, _ = agg([d['toks'] for d in plain])
    cO, _, _ = agg([content_tokens(human_all[i]['text']) for i in test_ids])
    cB, dfB, nB = agg([content_tokens(human_all[i]['text']) for i in base_ids])
    spread, per_model = defaultdict(set), {m: Counter() for m in MODELS}
    for d in skill:
        for u in units(d['toks']):
            spread[u].add(d['id']); per_model[d['model']][u] += 1
    tot = lambda c, n: sum(v for k, v in c.items() if ngram_n(k) == n)
    T = {(k, n): tot(c, n) for k, c in (('S', cS), ('N', cN), ('O', cO), ('B', cB)) for n in (1, 2, 3)}
    rows = []
    for u, cnt in cS.items():
        n = ngram_n(u)
        if dfS[u] < 6 or len(spread[u]) < 4 or sum(per_model[m][u] >= 1 for m in MODELS) < 2:
            continue
        z_h = log_odds_z(u, cS, cO, T[('S', n)], T[('O', n)], cB, T[('B', n)])
        z_n = log_odds_z(u, cS, cN, T[('S', n)], T[('N', n)], cB, T[('B', n)])
        r = lambda c, k: c.get(u, 0) / T[(k, 1)] * 1e3
        if z_h < 3 and z_n < 3:
            continue
        rows.append({'unit': u, 'z_vs_human': round(z_h, 1), 'z_vs_noskill': round(z_n, 1),
                     'skill_per1k': round(r(cS, 'S'), 3), 'noskill_per1k': round(r(cN, 'N'), 3),
                     'human_orig_per1k': round(r(cO, 'O'), 3), 'human_base_per1k': round(r(cB, 'B'), 4),
                     'skill_docs': dfS[u], 'topics': len(spread[u]), 'models': {m: per_model[m][u] for m in MODELS}})
    rows.sort(key=lambda x: -(x['z_vs_human'] + x['z_vs_noskill']))
    raw = [(f"{d['model']}/{d['id']}", TODO.sub('[TODO]', d['raw'])) for d in skill]
    for x in rows[:150]:
        x['examples'] = contexts(x['unit'], raw, 4)
    (HERE / 'results').mkdir(exist_ok=True)
    json.dump(rows, open(HERE / 'results/skill_surface_terms.json', 'w'), indent=1)
    print(len(rows), 'terms')
    for x in rows[:90]:
        print(f"{x['unit']:30s} zH={x['z_vs_human']:5.1f} zN={x['z_vs_noskill']:5.1f} S={x['skill_per1k']:6.3f} N={x['noskill_per1k']:6.3f} H={x['human_base_per1k']:6.3f} docs={x['skill_docs']:3d} {x['models']}")


if __name__ == '__main__':
    main()
