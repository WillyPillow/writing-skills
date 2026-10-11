# Review: "How we cut PR CI from 41 minutes to 12"

Reviewed against material.md only. Findings are ordered top-down by level. The draft's existing `[TODO: ...]` markers are correct uses of the rule on gaps and are not repeated here unless a finding changes them.

## Substance

1. Substance, "Bigger runners, tried and reverted", the TODO, and "The lesson", first paragraph. The material lists the steps "in order", and the runner trial is third, after sharding and the remote cache. The material's own reason ("the long pole was the serial integration job") only holds if the trial ran before sharding, so the material is inconsistent. The TODO asks the right question but does not say the material already gives an order. Meanwhile "The lesson" states the before-sharding version as fact: "Before this work, one job ran for 22 minutes on its own ... Twice the cores saved 3 minutes." Fix: in the TODO, add "The notes list the trial third, after sharding and caching; which is right?". Until the author answers, mark the lesson's sentence "Twice the cores saved 3 minutes." with `[TODO: depends on when the runner trial ran]`.

2. Substance, "What it cost", "the bigger runners would have doubled the cost of every job". The material says only "Cost 2x". "Every job" is a universal claim that the material does not support, and the TODO in the runners section already asks whether "2x" is the price or measured spend. Fix: "the bigger runners cost twice as much and saved 3 minutes at the median."

3. Substance, "The setup", "measured over all PRs in each month". The material gives the run counts (3,912 and 4,307) but does not say these were all PR runs in the month. Fix: "measured over 3,912 PR runs in July and 4,307 in September", or drop "over all PRs in each month" and keep the counts from the previous sentence.

4. Substance, "The setup", "Three steps took most of the time." The material gives the durations of the three steps (22, 9 and 6 minutes) but does not say they made up most of the 41-minute median. Whether they did depends on the critical path, which the TODO below this sentence asks for. Fix: "Three steps were the slowest." or mark the claim `[TODO: confirm these three dominated the run time]`.

5. Substance, "Caching the builds", "71% of build tasks hit the cache". The material says "Cache hit rate 71% on PRs" without a unit. "Build tasks" may be right for Turborepo but is not in the material. Fix: "On PRs, the cache hit rate was 71%", or confirm the unit with the author.

6. Substance, title. "Cut PR CI from 41 minutes to 12" drops the scope. Both figures are medians, and the p90 went from 58 to 19. Fix: "How we cut median PR CI time from 41 minutes to 12".

7. Substance, length. The request asks for 1,200 to 1,800 words. The draft has about 960 words of prose excluding the TODO markers. Most open TODOs, such as the pipeline diagram, how the critical path was found, one false-green case and the Dockerfile lines, would add real content. Fix: none in the text. Raise it with the author, and do not pad.

## Argument

8. Argument, "Bigger runners, tried and reverted", placement. This section comes right after the reader learns that the integration job is now six 5-minute shards. Then it says "The serial integration job was still the long pole". A first-time reader sees a contradiction, whichever order the trial actually ran in. Fix: once the author confirms the order (finding 1), place the section where the order puts it. If the trial came first, move it above "Splitting the integration tests" and open it with "Before sharding, we tried ...".

9. Argument, terms for the critical path. The post's central lesson uses three names for one concept: "critical path" (intro, setup TODO), "long pole" (runners section) and "the chain of jobs that sets your wall time" (lesson). The definition comes only in the last section. Fix: define the term at its first use in "The setup" ("the critical path, the chain of jobs that sets a run's wall time") and use "critical path" in the lesson. "Long pole" can stay only if it is defined as the longest job on the critical path.

10. Argument, "The lesson", first paragraph. It restates the introduction (22-minute floor, 3 minutes from twice the cores, 41 to 12, 18% more spend) and adds nothing for its own section. Fix: delete the paragraph and open the section with "Before you buy bigger machines, find ...". The intro already carries the numbers.

11. Argument, "What sharding shook loose", "If you shard a suite that has always run in one order, expect the same." This generalizes from one suite. Fix: narrow it to "If you shard a suite that has always run in one order, it may expose order-dependent tests, as ours did." or cut the sentence and keep the next one.

## Design

No findings. The two decisions in the post, reverting the bigger runners and turning off Go test selection, each give their reason and their cost (subject to findings 1 and 2).

## Math

Not applicable.

## Sentences

12. Sentences, "The short version", intro paragraph 2, "This post covers what we changed, what we tried and backed out, and what it cost." This sentence is a signpost about the post's layout and a list of three, and removing it loses nothing. Fix: delete it and keep "The short version: find the critical path before you buy hardware."

13. Sentences, "Splitting the integration tests", "Splitting the tests evenly needs to know how long each one takes." The gerund subject "needs to know" something. Fix: "To split the tests evenly, we need the duration of each test."

14. Sentences, "Splitting the integration tests", "The 22-minute integration job was a single job". Calling it a "job" twice says nothing new. Fix: "The integration tests ran as one 22-minute job, so nothing else we did could bring a run below 22 minutes."

15. Sentences, "Running less, where it's safe", "A test selector that misses some dependencies turns CI from a check into a guess". This is a figure that performs rather than informs, and it is also a broad claim. Fix: "A selector that misses dependencies lets a broken test pass CI, so Go tests always run in full."

16. Sentences, "Running less, where it's safe", "the slowest part of the full run takes 5 minutes". "Part" is vague, and the post's term is "shard". Fix: "the slowest shard takes 5 minutes."
