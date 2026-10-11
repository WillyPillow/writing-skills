# Before and after: technical-writing

Each directory here holds one complete document written twice from the same material, once without the `technical-writing` skill and once with it. Read the two side by side and judge which one you would rather review, build from or learn from.

| Directory | Document |
| --- | --- |
| [`design-doc`](design-doc/) | A design doc that moves web sessions from server memory to signed cookies |
| [`adr`](adr/) | An architecture decision record choosing a Postgres table as a job queue |
| [`paper`](paper/) | A four-page workshop paper on a sketch-based join size estimator |
| [`blog-post`](blog-post/) | An engineering blog post on cutting CI time from 41 to 12 minutes |
| [`lecture-notes`](lecture-notes/) | Undergraduate lecture notes on FKS perfect hashing |

## Files

Each directory has the same files:

- `material.md`: the request and the author's notes. This is the only input either version had. The systems, people, incidents and numbers in it are invented; the citations in the paper's material and the mathematics in the lecture notes are real.
- `before.md`: the document written without the skill.
- `after.md`: the document written with the skill, after its review pass.
- `draft.md`: the skill-guided draft before review.
- `review.md`: the review of `draft.md`, written by a separate agent following the skill's review pass.
- `notes-to-author.md`: the planning notes and open questions the skill keeps out of the document.

## How the documents were made

Every document was written by the same Claude model, run as a Claude Code subagent that could read only the files named here. No author was available to answer questions, so wherever the skill says to ask the author, the skill-guided agents marked the gap with `[TODO: ...]` and wrote their questions to `notes-to-author.md`.

1. **Before.** A fresh agent read `material.md` and wrote the requested document. It was told not to load any skill.
2. **Draft.** A second fresh agent read [`technical-writing/SKILL.md`](../../technical-writing/SKILL.md) and `material.md`, wrote its planning notes, and drafted `draft.md`.
3. **Review.** A third fresh agent, which had not seen the drafting, reviewed `draft.md` against `material.md` following the skill's review pass, and wrote `review.md`.
4. **Revision.** A fourth fresh agent applied the review to the draft, following the skill's rules for revising, and wrote `after.md`.

Each version is a single generation, not the best of several. Generation is not deterministic, so a rerun gives different documents.

## What to look for

The material in each directory leaves something out or contains a tension that a good document has to deal with:

- In `design-doc`, the security team has not signed off on how sessions are revoked, and the proposed fix brings back the per-request database read the design exists to avoid.
- In `adr`, the chosen queue table has not been shown to keep one customer's webhooks in order, which is one of the stated requirements.
- In `paper`, the method is less accurate than the sampling baseline, so the paper's claim has to rest on cost rather than accuracy.
- In `blog-post`, one change was reverted and another was turned off after false greens, and the speed-up raised the bill.
- In `lecture-notes`, the material is complete and correct, so the test is exposition: whether the notes motivate each step and answer the questions students ask.

The material also has gaps that were not planned. The paper's notes say the Count-Min sketch covers the joint key values, which does not fit the estimation formula, and never define the uniform term for light keys. The blog post's notes list the bigger-runner trial after sharding, but explain its failure by the unsharded integration job.

Things to check in either version: numbers or claims that are not in the material, alternatives presented as considered that the author never mentioned, advantages asserted without evidence, and gaps smoothed over instead of marked.

## What the pairs show

| Document | Words, before | Words, after | `[TODO]` markers, after |
| --- | --- | --- | --- |
| `design-doc` | 1,380 | 2,489 | 35 |
| `adr` | 959 | 1,233 | 31 |
| `paper` | 2,220 | 2,594 | 36 |
| `blog-post` | 1,318 | 1,130 | 10 |
| `lecture-notes` | 1,493 | 1,590 | 3 |

The "before" documents are fluent and well organized, and every number in them matches the material. Their weakness is what they add. Each one fills gaps with plausible statements the material does not contain:

- `adr`: "Jobs can be enqueued in the same transaction as the business data that produces them", listed as an advantage of Postgres. The material also gives cross-cloud hosting as the reason SQS lost; the before document gives it against Kafka too.
- `blog-post`: a three-line Dockerfile presented as the fix. It also repeats the material's explanation of the bigger-runner trial without noticing that the explanation contradicts the order of events.
- `design-doc`: "CSRF protection, as today" and "Nothing in the list above is secret from the user it belongs to".
- `paper`: "a few popular movies account for a large share of the rows in both `cast_info` and `movie_keyword`", an extension "that requires no changes to the PostgreSQL source", a definition of the heavy-key set and of the light-key term, and full author lists for the references, supplied from memory.
- `lecture-notes`: a concrete universal family and the article's volume and pages, both correct but not in the material.

The "after" documents add none of these. Where the material is silent, they ask, and the gaps they mark include both of the unplanned ones above. The skill-guided documents also caught problems that the before documents missed:

- `design-doc` notes that during a rolling deploy, servers with the new signing key and servers without it run side by side for about 24 minutes, which logs out users unless the key is rolled out in two steps.
- `adr` compares the three options on the same rows, which shows that per-customer ordering is the one requirement the brokers meet out of the box and the chosen option does not yet meet.
- `paper` opens with the JOB 16b misestimate before stating the method, and says plainly that JOB does not separate SkewSketch from sampling on runtime.
- `lecture-notes` handles lookups that land in an empty bucket. The before version's lookup calls a second-level hash function that was never drawn for that bucket.

Some of these catches are in the before versions too. The before design doc also flags that encoding may push the largest cookie past 4 KB, and that a stolen cookie that keeps being refreshed stays valid past 12 hours.

The cost is readability. With 31 to 36 markers, the after versions of `design-doc`, `adr` and `paper` are drafts for the author to finish, not documents a reviewer could read today. Some markers ask for real decisions, such as which actions count as sensitive. Others ask about choices that rarely need a reason, such as why keys rotate quarterly or why the signature is HMAC-SHA256. The `adr` comparison table has six cells reading "[TODO: compared?]". With an author available to answer the planning questions, as the skill expects, most of these markers would be answered before drafting. Here no one could answer them. The blog post and lecture notes, whose material left less open, read as finished documents.

The examples show how the skill changes one model's output on five inputs. They are not a measurement. For counts over hundreds of documents, see [`research/rfc-slop-forensics`](../../research/rfc-slop-forensics/README.md).
