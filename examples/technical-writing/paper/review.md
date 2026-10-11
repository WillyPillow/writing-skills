# Review: SkewSketch workshop paper (draft.md)

I checked every number in the draft against material.md, including the derived ratios (8x, 12x, 25x, 145x, 2.3x, 1.8x, about 14x, 17%, about 100x, q-error 2,400 and 1.4). All of them match. No experiment, number or citation is invented. The existing `[TODO: ...]` markers correctly flag gaps in the material. The findings below are ordered top-down.

## Substance

1. Substance, Section 1, paragraph 3, "The uniformity assumption persists because it is cheap.": this causal claim about why optimizers keep the assumption is not in the material. Fix: write "The uniformity assumption is cheap." or mark "[TODO: source for why optimizers keep the uniformity assumption]".

2. Substance, Section 1, paragraph 3, "on STATS-CEB some of them do not improve end-to-end runtime [2]": the material reports Han et al.'s finding with no benchmark attached ("some don't improve end-to-end runtime"). The draft narrows it to STATS-CEB, a scope the material does not give. Fix: delete "on STATS-CEB", or ask the author to confirm that scope.

3. Substance, three places that drop "median" from the estimation-overhead figures:
   - Abstract, "It takes 0.4 ms per query to estimate, against 41 ms"
   - Section 6, "Sampling", "estimates from them in 0.4 ms"
   - Section 8, "at 0.4 ms of estimation per query" and "at 41 ms per query"

   The material gives these as medians, and Sections 5.1 and 5.3 say so. Fix: insert "median" in each, for example "It takes a median of 0.4 ms per query to estimate".

4. Substance, Section 8, "restricting heavy-hitter estimation to the join-column pairs that test as correlated removes most of PostgreSQL 16's tail error": this credits the gain to the restriction. The material only evaluates SkewSketch as a whole. It has no variant that applies heavy hitters to every pair. Fix: "On JOB and STATS-CEB, SkewSketch removes most of PostgreSQL 16's tail error".

5. Substance, Section 5.3, paragraph 2, "the difference between them shows in estimation latency and memory": the material gives no size for Sample1%'s sample, and Table 2 marks it "[TODO: size in MB]". So no memory comparison exists. Fix: end the sentence at "estimation latency", or keep "and memory" only once the author supplies the sample size.

6. Substance, Abstract, "a few megabytes of memory": the measured figures are 14 MB and 9 MB. Fix: "9 to 14 MB of memory".

## Argument

7. Argument, Section 1, paragraph 4 and Section 3.1: the paper's central design choice has no stated reason. That choice is to apply heavy-hitter estimation only to pairs that pass a chi-square test, and to fall back to PostgreSQL everywhere else. A reviewer's first objection will be "why not use heavy-hitter frequencies for every join?" The material gives no reason, and the existing TODO in 3.1 asks only about the thresholds. Fix: add after the first sentence of 3.1 "[TODO: why restrict heavy-hitter estimation to correlated pairs rather than all join pairs (build time, memory, accuracy on uncorrelated pairs)? Give the measurement if there is one.]"

8. Argument, title ("Correlated Keys") and Section 1, paragraph 4 ("SkewSketch targets joins on skewed keys"), and Section 3.2, paragraph 2: the method selects pairs by a correlation test. The explanation of why Eq. (1) helps rests on skew, where the same few keys are frequent on both sides. Nothing says why a pair that passes the chi-square test has shared heavy keys, so a reader cannot connect the selection rule to the mechanism. Fix: in 3.2, after "Eq. (1) counts them directly", add "[TODO: what does the chi-square test detect in a join-column pair, and why do pairs that pass it have keys that are frequent on both sides?]". Then use one of "correlated" and "skewed" for the joins SkewSketch targets.

9. Argument, Section 1, paragraph 3, "must correct the large errors without adding this cost": "this cost" could mean sampling's per-query time or learned estimators' training time. On the second reading, SkewSketch's own offline build breaks the requirement the paragraph sets. Fix: "without adding tens of milliseconds per query".

10. Argument, Sections 2 and 3.1, Count-Min sketch: Section 2 defines it and Section 3.1 builds it, but Eq. (1) uses only heavy-hitter frequencies and U_light. As written, the sketch is an unused object. The TODO in 3.1 already asks what it supplies. Fix: once the author answers, say in 3.2 which term of Eq. (1) reads the sketch. If no term does, cut the sketch from Sections 2 and 3.1.

11. Argument, Section 6, "Learned estimators", first sentence, "Han et al. [2] found that learned estimators improve accuracy but cost training time, and that some of them do not improve end-to-end runtime.": this sentence repeats Section 1, paragraph 3 almost word for word. The paragraph's positioning sentences carry the new content. Fix: delete the sentence, and change "Han et al.'s finding shows" to "Han et al.'s finding [2] (Section 1) shows".

## Design

No findings at this level beyond finding 7. This is a paper, and its main method choice is covered there.

## Math

No findings. Eq. (1) is numbered, punctuated and referred to, and each of its symbols is defined at its introduction. The prose around it still reads correctly with the formula replaced by "blah". The open points (the set H, U_light, multi-join composition, the light-key bound) are already marked with TODOs.

## Sentences

12. Sentences, one concept under three names: "independent and uniformly distributed" (Abstract, Section 1 paragraph 1), "uniformity assumption" (Section 1 paragraph 3) and "uniform assumption" (Sections 3.2, 5.2). Fix: use "uniformity assumption" throughout, introduced in Section 1 paragraph 1 as "the uniformity assumption: join keys are independent and uniformly distributed".

13. Sentences, one quantity under three names: "estimation overhead" (Sections 1, 5.1, Table 2), "estimation cost" (Abstract) and "estimation latency" (Section 5.3). Fix: use "estimation overhead" throughout.

14. Sentences, one baseline under several names: once defined in Section 5.1, the baseline also appears as "1% join sampling" (contribution 3, Section 7) and "join sampling" (Section 8). Fix: use "Sample1%" after Section 5.1, or else "1% join sampling" consistently outside Section 5.

15. Sentences, Section 5.2, paragraph 2, last sentence (about 45 words): it repeats the join, the columns and the row counts from Section 1, although it already points there with "the example from Section 1". Fix: "In JOB 16b, the example from Section 1, PostgreSQL's estimate has a q-error of about 2,400. SkewSketch's has a q-error of 1.4 [TODO: Sample1%'s estimate for this join]."

16. Sentences, long sentences that each introduce two facts:
   - Section 1, paragraph 4, "It tests each pair of join columns ... its 1,000 most frequent keys." (about 30 words). Fix: split after "offline". "It tests each pair of join columns for correlation offline. For the pairs that test as correlated, it keeps the frequencies of each column's heavy hitters, its 1,000 most frequent keys."
   - Section 5.3, paragraph 2, "Sample1% reaches 153 s ... does not give it a faster total." (about 31 words). Fix: "Sample1% reaches 153 s including its sampling time, within 2 s of SkewSketch. Its higher accuracy does not give it a faster total."

The draft's existing TODOs are gaps in the material, not findings. Three of them block a reviewer from checking the method or the results:
- how Eq. (1) combines across multi-join queries (3.2)
- the hardware and configuration (5.1)
- STATS-CEB runtime (5.3)
