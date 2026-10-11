# Claude-written and human-written PEPs and Rust RFCs

This directory holds the comparison behind three rules in the `technical-writing` skill: universal, compatibility and cost claims need support; notes to the author stay out of the document's prose; and the decision-record terms are a checklist, not vocabulary for the document. The skill does not depend on anything here.

The question was whether the "slop" lists used by EQ-Bench, or a list built the same way for technical writing, can separate LLM-written design documents from human-written ones. EQ-Bench's lists cannot. A list built for this genre can, and the terms on it point to a kind of claim rather than to a vocabulary.

## Method

1. **Human corpus.** Python PEPs and Rust RFCs started in 2021 or earlier, with code blocks, inline code, URLs and metadata removed (`prep_human.py`). That leaves 1,097 documents and 1.9 million words of prose.
2. **Topics.** 120 documents, 60 PEPs and 60 RFCs, each with 1,000 to 6,000 words of prose and an abstract or summary (`select_prompts.py`). Every third topic is held out, giving 80 training topics and 40 test topics.
3. **LLM corpus.** Claude Opus, Sonnet and Haiku each wrote all 120 documents from the original title and abstract, in Claude Code subagents that could read only their prompt file (`generate.workflow.js`). The 360 documents, about 463,000 words, are in `data/llm_corpus/`.
4. **Ranking** (`analyze.py`). Words, bigrams and trigrams are tokenized with the slop-forensics tokenizer, without stopwords. The stock slop-forensics pipeline compares words against general English (wordfreq), which in this genre surfaces technical vocabulary. Instead, each term in the 240 training documents is compared with the 80 human originals on the same topics, using log-odds with an informative Dirichlet prior (Monroe, Colaresi and Quinn 2008). A term is kept if it has z ≥ 3 against the originals, is at least twice as frequent as in the full human baseline, appears in at least 8 documents and 5 topics, and appears in at least 2 documents from each of at least 2 models.
5. **Held-out test.** The list is scored on the 120 LLM documents for the 40 test topics, against the 40 human originals and 160 further human documents that were left out of the baseline. AUC is the probability that a random LLM document has more list hits per 1,000 tokens than a random human document; 0.5 is chance.

## Results

All numbers below are in `results/`.

| List | AUC, LLM test documents vs all held-out human documents |
| --- | --- |
| EQ-Bench slop-score words and trigrams | 0.41 to 0.52, depending on the model |
| This list, all 161 terms | 0.954 (against the 40 originals and against the other 160 alike) |
| This list without the 32 template-heading and topic terms (129 terms) | 0.961 |
| Same, against human documents from 2018 to 2021 only | 0.951 |
| Template-heading and topic terms only, against 2018 to 2021 | 0.663 |

The template headings, such as "guide-level explanation", come from the current Rust RFC template, which newer human RFCs also follow. They lose most of their separating power against recent documents, so they are an era artifact. The remaining terms keep it.

Those remaining terms are plain words: "every", "cannot", "already", "keeps", "leaves", "unaffected", "silently", "cost", "callers". In context, most of the sentences that use them read well. What they share is a kind of claim, stated as fact. `claim_families.py` counts four such families with regular expressions (rates per 1,000 words):

| Family | Opus | Sonnet | Haiku | Human, same topics | Human, 2018 to 2021 | Human, all |
| --- | --- | --- | --- | --- | --- | --- |
| Universal claims (every, nothing, cannot, already, ...) | 7.37 | 5.83 | 4.37 | 2.94 | 2.96 | 2.95 |
| Compatibility claims (unaffected, keeps working, ...) | 0.78 | 0.77 | 1.05 | 0.16 | 0.14 | 0.14 |
| Cost claims (the cost, the overhead, ...) | 0.36 | 0.50 | 0.70 | 0.08 | 0.07 | 0.07 |
| silently, deliberately, intentionally | 0.51 | 0.40 | 0.38 | 0.11 | 0.14 | 0.11 |

The models had only a title and an abstract, with no benchmarks or compatibility data. Any compatibility or cost claim beyond what an abstract stated had no support in their material.

The cost pattern is broad: it also counts trade-off statements such as "the cost is that downstream crates lose struct literal construction", which the skill asks for. The narrower patterns in `compare_skill.py` give performance claims (overhead, faster, slower, ...) at 1.1 to 1.7 times the human rate across the full corpus, and trade-off statements at 1.4 to 1.7 times. The skill therefore cites only the compatibility figure. The compatibility pattern also counts a few negations, such as "existing code is affected".

## With the skill

`generate_skill.workflow.js` had each model write the 40 test topics again while following `technical-writing/SKILL.md` as of commit `6294586`. That version includes the rule this comparison produced. The title and abstract were the whole of the author's material. No author could answer questions, so wherever the skill says to ask, the models marked `[TODO: ...]` instead. They also ran the skill's review pass themselves. `compare_skill.py` compares the 120 documents with the no-skill documents on the same topics and with the 40 human originals. `[TODO]` text is removed before counting. Results are in `results/skill_comparison.json`.

| Per 1,000 words | Opus | Opus, skill | Sonnet | Sonnet, skill | Haiku | Haiku, skill | Human originals |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Median length (words) | 1,067 | 976 | 1,274 | 769 | 1,150 | 370 | |
| `[TODO]` markers per document | 0 | 11.9 | 0 | 17.6 | 0 | 16.6 | |
| Compatibility claims | 0.99 | 0.90 | 1.00 | 0.49 | 1.30 | 0.69 | 0.26 |
| Performance claims (overhead, faster, ...) | 0.53 | 0.26 | 0.33 | 0.36 | 0.28 | 0.12 | 0.14 |
| Numeric quantities (ms, %, MB, ...) | 0.07 | 0.13 | 0.04 | 0.00 | 0.09 | 0.00 | 0.23 |
| Trade-off statements (the cost is, drawback, ...) | 0.46 | 1.22 | 0.63 | 1.44 | 0.48 | 0.75 | 0.32 |
| Suggestion labels (for the author to evaluate, ...) | 0.09 | 0.82 | 0.16 | 2.06 | 0.24 | 1.04 | 0.47 |
| Register-list AUC against human documents | 0.955 | 0.968 | 0.949 | 0.985 | 0.978 | 0.975 | |

With the skill, the models left gaps open instead of filling them: 12 to 18 `[TODO]` markers per document. Haiku's documents shrank to a median of 370 words. Compatibility claims fell for Sonnet and Haiku but barely for Opus. Performance claims halved for Opus and Haiku, but not for Sonnet. The few numbers left in the Opus documents are worked examples, such as 1.9999 ms rounding to 1 ms. Trade-off statements and suggestion labels rose, which is what the skill's decision-record and labelling rules ask for.

The register list separated the skill documents from human documents at least as well as before. Its terms are plain verbs, named actors and stated obstacles ("keeps", "callers", "cannot"), which the skill's sentence rules encourage. The list therefore identifies Claude's writing; it does not measure quality, and lowering a document's score is not a goal.

The cost-claim family in `claim_families.py` rose with the skill, from two- to seven-fold. Its pattern counts any "the cost" or "costs", and the added sentences are the trade-off statements the skill requires. The narrower patterns above separate trade-offs from performance claims. The compatibility pattern also counts negations such as "existing code is affected", so its rates are approximate.

### Bad patterns in the skill documents

`surface_patterns.py` runs the same over-use analysis on the skill documents, against the human originals and against the no-skill documents on the same topics (`results/skill_surface_terms.json`). `known_patterns.py` counts the patterns found that way, together with the skill's own scan list, EQ-Bench's not-x-but-y detector and typography (`results/known_patterns.json`). Text inside `[TODO]` markers is removed first.

| Per 1,000 words | Opus | Opus, skill | Sonnet | Sonnet, skill | Haiku | Haiku, skill | Human originals |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Skill vocabulary in the prose ("the force behind this decision", "deciding reason", "expensive to reverse", "central tension") | 0 | 0.92 | 0 | 2.19 | 0 | 2.07 | 0 |
| Review notes in the prose ("the abstract says", "the material does not record", "this is a compatibility claim, and it needs evidence") | 0.05 | 0.29 | 0.02 | 3.98 | 0.09 | 9.84 | 0.02 |
| Headings | 13.9 | 14.5 | 12.0 | 19.4 | 7.6 | 24.0 | 8.5 |
| Bold-label bullets, per 100 lines | 2.47 | 0 | 2.18 | 0.34 | 0.35 | 0.27 | 0.05 |
| Em dashes | 0.57 | 0 | 0.06 | 0 | 0 | 0 | 0.56 |
| Stock vocabulary and stock significance (scan list) | 0.35 | 0.32 | 0.41 | 0.23 | 0.30 | 0.12 | 0.42 |
| EQ-Bench not-x-but-y, per 1,000 characters | 0.030 | 0.027 | 0.039 | 0.005 | 0.046 | 0.019 | 0.033 |

The skill's scan-list items were already rare without the skill, at or below the human rates. The skill removed the bold-label bullets and em dashes that Opus and Sonnet otherwise used. It also introduced two patterns that no other corpus has. First, the decision-record terms the skill uses as a checklist appear as prose: "The force behind this decision is ...", "This is the decision that is most expensive to reverse, so it needs the most justification." Second, notes meant for the author appear in the body outside any `[TODO]` marker: "The supplied material states the security side of the argument in detail and says nothing about the reproducibility side." With most of the material missing, Sonnet and Haiku produced short documents with many headings and little prose under them.

The setup contributed to the second pattern: the models had only a title and an abstract, and no author to ask, whereas the skill expects the author to correct a plan before any drafting.

## Limitations

- All generated documents come from Claude models, run as Claude Code subagents rather than through the plain API, so the results describe Claude in that setting.
- The models may have recognized some of the 2021-or-earlier documents, although the prompt told them not to reproduce them.
- The split between register terms and template or topic terms is a manual judgment over 32 terms (`TEMPLATE` and `TOPIC` in `analyze.py`).
- The human corpus comes from two open-source projects. Company design docs, papers and blog posts were not tested.
- The claim-family patterns are regular expressions. They count phrases, not whether a claim was supported.

## Reproducing

Python 3.10 or later with no extra packages is enough for the analysis. `fetch_sources.sh` uses git, and `known_patterns.py` uses Node.js 18 or later for EQ-Bench's detector.

```sh
./fetch_sources.sh          # clone the corpora and slop tooling at pinned commits into sources/
python3 prep_human.py       # extract prose into build/human_docs.json
python3 select_prompts.py   # rewrite data/prompts.json and data/batches/ (byte-identical to the committed ones)
python3 analyze.py          # write results/forensics.json and results/checks.json
python3 claim_families.py   # write results/claim_families.json
python3 compare_skill.py    # write results/skill_comparison.json
python3 surface_patterns.py # write results/skill_surface_terms.json
python3 known_patterns.py   # write results/known_patterns.json (needs node)
```

To regenerate the LLM corpus instead of using the committed one, run `generate.workflow.js` with the Workflow tool in Claude Code, passing `{"dir": "<absolute path of this directory>"}`. Generation is not deterministic, so a new corpus will give somewhat different numbers.

`results/forensics.json` lists every term with its rates, its z-score, its held-out ratio and example sentences from both corpora.

## Sources and licenses

- Python PEPs: <https://github.com/python/peps> at `545c670f`. PEPs are placed in the public domain or under CC0-1.0.
- Rust RFCs: <https://github.com/rust-lang/rfcs> at `d2705ad6`, under MIT or Apache-2.0.
- slop-score (EQ-Bench slop lists): <https://github.com/sam-paech/slop-score> at `289264ab`, MIT.
- slop-forensics (tokenizer): <https://github.com/sam-paech/slop-forensics> at `c313f042`, MIT.
- Monroe, Colaresi and Quinn, "Fightin' Words: Lexical Feature Selection and Evaluation for Identifying the Content of Political Conflict", *Political Analysis* 16(4) (2008).

`data/prompts.json` and `data/batches/` quote titles and abstracts from the PEPs and RFCs above, under their licenses. The scripts and generated documents fall under the repository's Unlicense.
