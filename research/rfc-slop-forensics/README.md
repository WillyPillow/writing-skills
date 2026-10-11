# Claude-written and human-written PEPs and Rust RFCs

This directory holds the comparison behind one rule in the `technical-writing` skill: universal, compatibility and cost claims need support. The skill does not depend on anything here.

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

## Limitations

- All generated documents come from Claude models, run as Claude Code subagents rather than through the plain API, so the results describe Claude in that setting.
- The models may have recognized some of the 2021-or-earlier documents, although the prompt told them not to reproduce them.
- The split between register terms and template or topic terms is a manual judgment over 32 terms (`TEMPLATE` and `TOPIC` in `analyze.py`).
- The human corpus comes from two open-source projects. Company design docs, papers and blog posts were not tested.
- The claim-family patterns are regular expressions. They count phrases, not whether a claim was supported.

## Reproducing

Python 3.10 or later with no extra packages is enough for the analysis. `fetch_sources.sh` uses git.

```sh
./fetch_sources.sh          # clone the corpora and slop tooling at pinned commits into sources/
python3 prep_human.py       # extract prose into build/human_docs.json
python3 select_prompts.py   # rewrite data/prompts.json and data/batches/ (byte-identical to the committed ones)
python3 analyze.py          # write results/forensics.json and results/checks.json
python3 claim_families.py   # write results/claim_families.json
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
