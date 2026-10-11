"""Rank terms LLM-written PEPs/RFCs over-use relative to human-written ones, and test the list on held-out topics.

Usage: python3 analyze.py   (needs sources/, build/human_docs.json, data/; writes results/forensics.json and results/checks.json)

Tokenization reuses slop-forensics' normalize_text/extract_words with NLTK's English stopword list (inlined).
Ranking replaces slop-forensics' comparison against general English (wordfreq) with a comparison against
human-written documents on the same topics: log-odds with an informative Dirichlet prior (Monroe, Colaresi
and Quinn 2008), then held-out validation.
"""
import importlib.util, json, math, pathlib, random, re
import statistics as st
from collections import Counter, defaultdict

from prep_human import md_prose

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sfu', HERE / 'sources/slop-forensics/slop_forensics/utils.py')
sfu = importlib.util.module_from_spec(spec); spec.loader.exec_module(sfu)

MODELS = ('opus', 'sonnet', 'haiku')
STOP = set("i me my myself we our ours ourselves you your yours yourself yourselves he him his himself she her hers herself it its itself they them their theirs themselves what which who whom this that these those am is are was were be been being have has had having do does did doing a an the and but if or because as until while of at by for with about against between into through during before after above below to from up down in out on off over under again further then once here there when where why how all any both each few more most other some such no nor not only own same so than too very s t can will just don should now d ll m o re ve y ain aren couldn didn doesn hadn hasn haven isn ma mightn mustn needn shan shouldn wasn weren won wouldn".split())
META = re.compile(r'^\W*(PEP|Title|Authors?|Status|Type|Topic|Created|Python-Version|Post-History|Feature Name|Start Date|RFC PR|Rust Issue|Requires|Replaces|Discussions-To|Content-Type|Resolution|Sponsor|BDFL-Delegate)\s*:.*$', re.M | re.I)
# Terms excluded from the register-only check: Rust RFC template headings (an era artifact) and topic words.
TEMPLATE = {'level explanation', 'reference level explanation', 'reference level', 'guide level explanation', 'guide level',
            'rationale alternatives', 'summary rfc', 'open issues', 'reference implementation', 'implementation reference',
            'implementation reference implementation', 'motivation rust', 'rust rfc'}
TOPIC = {'interpreter', 'compiler', 'field', 'registry', 'metaclass', 'unsafe', 'trait object', 'bounds', 'body', 'contract',
         'diagnostics', 'teams', 'contributors', 'warn', 'raises', 'rule', 'boundary', 'program', 'programs'}


def content_tokens(text):
    toks = sfu.extract_words(sfu.normalize_text(META.sub('', text)))
    out = []
    for t in toks:
        if t.endswith("'s"):
            t = t[:-2]                      # slop-forensics merges possessive 's
        if t and t not in STOP and len(t) > 1:
            out.append(t)
    return out


def units(tokens):
    u = Counter(tokens)
    u.update(' '.join(tokens[i:i + 2]) for i in range(len(tokens) - 1))
    u.update(' '.join(tokens[i:i + 3]) for i in range(len(tokens) - 2))
    return u


def agg(token_lists):
    c, df = Counter(), Counter()
    for t in token_lists:
        u = units(t); c.update(u); df.update(u.keys())
    return c, df, len(token_lists)


def ngram_n(u):
    return u.count(' ') + 1


def log_odds_z(u, ca, cb, a_tot, b_tot, prior_c, prior_tot, a0=500.0):
    """Monroe et al. (2008) log-odds with informative Dirichlet prior; returns the z-score."""
    aw = a0 * (prior_c.get(u, 0) + 0.5) / (prior_tot + 0.5)
    ya, yb = ca.get(u, 0), cb.get(u, 0)
    da = math.log((ya + aw) / (a_tot + a0 - ya - aw)); db = math.log((yb + aw) / (b_tot + a0 - yb - aw))
    return (da - db) / math.sqrt(1 / (ya + aw) + 1 / (yb + aw))


def auc(pos, neg):
    s = 0.0
    for p in pos:
        for q in neg:
            s += 1.0 if p > q else 0.5 if p == q else 0.0
    return s / (len(pos) * len(neg))


def score(du, lst):
    ntok = sum(v for k, v in du.items() if ' ' not in k)
    return sum(du.get(u, 0) for u in lst) / max(ntok, 1) * 1e3


def contexts(u, docs_raw, k=3):
    out = []
    pat = re.compile(r'\b' + r'\W+(?:\w+\W+){0,3}?'.join(map(re.escape, u.split())) + r'\b', re.I)
    for name, raw in docs_raw:
        for sent in re.split(r'(?<=[.!?])\s+|\n+', raw):
            if pat.search(sent):
                out.append(f"{name}: {sent.strip()[:220]}"); break
        if len(out) >= k:
            break
    return out


def main():
    prompts = {p['id']: p for p in json.load(open(HERE / 'data/prompts.json'))}
    human_all = {d['name']: d for d in json.load(open(HERE / 'build/human_docs.json')) if len(d['text'].split()) >= 300}

    llm = []
    for m in MODELS:
        for p in sorted((HERE / 'data/llm_corpus' / m).glob('*.md')):
            if p.stem not in prompts:
                continue
            raw = p.read_text(errors='replace')
            toks = content_tokens(md_prose(raw))
            if len(toks) < 200:
                continue
            llm.append({'model': m, 'id': p.stem, 'split': prompts[p.stem]['split'], 'toks': toks, 'raw': raw})

    # Human sets: the 40 test-topic originals and 160 other documents are held out of the baseline.
    rng = random.Random(7)
    test_orig = [i for i, p in prompts.items() if p['split'] == 'test']
    train_orig = [i for i, p in prompts.items() if p['split'] == 'train']
    others = sorted(set(human_all) - set(prompts))
    extra_test = rng.sample(others, 160)
    base_ids = [i for i in human_all if i not in set(test_orig) | set(extra_test)]
    H = {i: content_tokens(human_all[i]['text']) for i in human_all}

    L_tr = [d for d in llm if d['split'] == 'train']; L_te = [d for d in llm if d['split'] == 'test']
    cL, dfL, nL = agg([d['toks'] for d in L_tr])
    cP, dfP, nP = agg([H[i] for i in train_orig])          # paired, topic-matched originals
    cB, dfB, nB = agg([H[i] for i in base_ids])            # full human baseline (includes paired)
    per_model_df = {m: Counter() for m in MODELS}
    prompt_spread = defaultdict(set)
    for d in L_tr:
        for u in units(d['toks']):
            per_model_df[d['model']][u] += 1; prompt_spread[u].add(d['id'])
    tot = lambda c, n: sum(v for k, v in c.items() if ngram_n(k) == n)
    TOT = {(name, n): tot(c, n) for name, c in (('L', cL), ('P', cP), ('B', cB)) for n in (1, 2, 3)}

    # Candidates: in >= 8 train docs, >= 5 topics, >= 2 docs in at least 2 models;
    # z >= 3 against the paired originals and >= 2x the full-baseline rate.
    rows = []
    for u, cnt in cL.items():
        n = ngram_n(u)
        if dfL[u] < 8 or len(prompt_spread[u]) < 5:
            continue
        if sum(per_model_df[m][u] >= 2 for m in per_model_df) < 2:
            continue
        z = log_odds_z(u, cL, cP, TOT[('L', n)], TOT[('P', n)], cB, TOT[('B', n)])
        rL = cnt / TOT[('L', 1)] * 1e3                      # per 1k content tokens
        rP = cP.get(u, 0) / TOT[('P', 1)] * 1e3
        rB = cB.get(u, 0) / TOT[('B', 1)] * 1e3
        ratio_B = rL / max(rB, 0.5 / TOT[('B', 1)] * 1e3)
        if z < 3 or ratio_B < 2:
            continue
        rows.append({'unit': u, 'n': n, 'z_vs_paired': round(z, 2), 'llm_per1k': round(rL, 3), 'paired_per1k': round(rP, 3),
                     'base_per1k': round(rB, 4), 'ratio_vs_base': round(ratio_B, 1),
                     'llm_docfrac': round(dfL[u] / nL, 3), 'base_docfrac': round(dfB.get(u, 0) / nB, 3),
                     'prompts': len(prompt_spread[u]), 'models': {m: per_model_df[m][u] for m in per_model_df}})
    rows.sort(key=lambda r: -r['z_vs_paired'])

    # Held-out validation
    TE_L = [(d, units(d['toks'])) for d in L_te]
    TE_HO = [(i, units(H[i])) for i in test_orig]
    TE_HX = [(i, units(H[i])) for i in extra_test]
    frac = lambda docs, u: sum(1 for _, du in docs if u in du) / max(1, len(docs))
    rate = lambda docs, u: sum(du.get(u, 0) for _, du in docs) / max(1, sum(sum(v for k, v in du.items() if ' ' not in k) for _, du in docs)) * 1e3
    for r in rows:
        u = r['unit']
        r['test_llm_docfrac'] = round(frac(TE_L, u), 3)
        r['test_human_docfrac'] = round(frac(TE_HO + TE_HX, u), 3)
        r['test_llm_per1k'] = round(rate(TE_L, u), 3)
        r['test_human_per1k'] = round(rate(TE_HO + TE_HX, u), 4)
        r['test_ratio'] = round(r['test_llm_per1k'] / max(r['test_human_per1k'], 0.01), 1)
        r['confirmed'] = r['test_ratio'] >= 2 and r['test_llm_docfrac'] >= 0.03

    eq = [x[0].lower() for x in json.load(open(HERE / 'sources/slop-score/data/slop_list.json'))] + \
         [x[0].lower() for x in json.load(open(HERE / 'sources/slop-score/data/slop_list_trigrams.json'))]
    lists = {
        'tech list (train-derived, all candidates)': [r['unit'] for r in rows],
        'tech list, words only': [r['unit'] for r in rows if r['n'] == 1],
        'tech list, top 50 by z': [r['unit'] for r in rows[:50]],
        'EQ-Bench slop-score words+trigrams': eq,
    }
    aucs = {}
    for name, lst in lists.items():
        pos = [score(du, lst) for _, du in TE_L]
        aucs[name] = {'vs paired originals': round(auc(pos, [score(du, lst) for _, du in TE_HO]), 3),
                      'vs extra human': round(auc(pos, [score(du, lst) for _, du in TE_HX]), 3)}
        for m in MODELS:
            pm = [score(du, lst) for d, du in TE_L if d['model'] == m]
            aucs[name][m + ' vs all human'] = round(auc(pm, [score(du, lst) for _, du in TE_HO + TE_HX]), 3)

    llm_raw = [(f"{d['model']}/{d['id']}", d['raw']) for d in L_tr]
    human_raw = [(i, human_all[i]['text']) for i in base_ids]
    for r in rows[:400]:
        r['llm_examples'] = contexts(r['unit'], llm_raw)
        r['human_examples'] = contexts(r['unit'], human_raw, 2)

    summary = {'llm_docs': {m: sum(d['model'] == m for d in llm) for m in MODELS},
               'llm_train_docs': len(L_tr), 'llm_test_docs': len(L_te),
               'human_paired_train': len(train_orig), 'human_base_docs': len(base_ids),
               'human_test_paired': len(test_orig), 'human_test_extra': len(extra_test),
               'candidates': len(rows), 'confirmed': sum(r['confirmed'] for r in rows),
               'by_n': {n: sum(r['n'] == n for r in rows) for n in (1, 2, 3)}, 'auc': aucs}
    (HERE / 'results').mkdir(exist_ok=True)
    json.dump({'summary': summary, 'rows': rows}, open(HERE / 'results/forensics.json', 'w'), indent=1)
    print(json.dumps(summary, indent=1))

    # Robustness: register-only list, and era control against recent and old human documents.
    register = [r['unit'] for r in rows if r['unit'] not in TEMPLATE | TOPIC]
    years = {i: human_all[i]['year'] for i in human_all}
    recent = [(i, du) for i, du in TE_HO + TE_HX if years[i] >= 2018]
    older = [(i, du) for i, du in TE_HO + TE_HX if years[i] < 2010]
    checks = {}
    for name, lst in {'register-only (train-derived)': register, 'template+topic only': sorted(TEMPLATE | TOPIC)}.items():
        pos = [score(du, lst) for _, du in TE_L]
        checks[name] = {'n_terms': len(lst),
                        'vs all human test': round(auc(pos, [score(du, lst) for _, du in TE_HO + TE_HX]), 3),
                        f'vs human 2018-2021 (n={len(recent)})': round(auc(pos, [score(du, lst) for _, du in recent]), 3),
                        f'vs human pre-2010 (n={len(older)})': round(auc(pos, [score(du, lst) for _, du in older]), 3)}
        for m in MODELS:
            checks[name][m] = round(auc([score(du, lst) for d, du in TE_L if d['model'] == m], [score(du, lst) for _, du in TE_HO + TE_HX]), 3)
    rl = [score(du, register) for _, du in TE_L]; rh = [score(du, register) for _, du in TE_HO + TE_HX]
    checks['register hits per 1k content tokens, median LLM vs human'] = [round(st.median(rl), 1), round(st.median(rh), 1)]
    json.dump(checks, open(HERE / 'results/checks.json', 'w'), indent=1)
    print(json.dumps(checks, indent=1))


if __name__ == '__main__':
    main()
