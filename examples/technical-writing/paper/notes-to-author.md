# Notes to the author: SkewSketch workshop paper

You were not available before drafting, so I drafted from your notes as they stand. Every gap I could not fill from the material is marked `[TODO: ...]` in `draft.md`. These notes list the plan the draft follows and the questions behind those markers. Please correct the plan where it is wrong; the draft will need the same correction.

## Plan

**Reader.** A database researcher who knows query optimization and q-error, has heard of JOB, and may not know STATS-CEB, Count-Min or SpaceSaving in detail. The draft defines q-error, Count-Min and SpaceSaving briefly and does not explain what a join or a cardinality estimate is.

**The point (refutable).** On JOB and STATS-CEB, an estimator that keeps heavy-hitter frequencies only for join-column pairs that test as correlated cuts PostgreSQL 16's 95th-percentile q-error by 8x (JOB) and 12x (STATS-CEB) at a median estimation cost of 0.4 ms per query, a hundredth of the cost of 1% index-based join sampling, which remains more accurate. The claim fails if the tail improvement is small, if the overhead is not far below sampling's, or if the accuracy gain does not reach end-to-end runtime.

**The skeptic.**

1. "Sampling is more accurate on every statistic you report. Why not just sample?" Answered in the introduction and in Section 5.3: the paper's claim is accuracy for the cost, and Table 2 sets 0.4 ms against 41 ms per query and 14 MB against a 1% copy of the data. The honest weak point: on JOB end-to-end, SkewSketch (151 s) and Sample1% (153 s) are within 2 s, so the material does not yet show a workload where sampling's 41 ms matters. See question 9.
2. "Learned estimators already fix this." The paper has no learned baseline. Related work positions SkewSketch against Han et al.'s findings (training cost, uneven end-to-end gains), but makes no accuracy comparison. See question 10.
3. "Static data only; the sketch goes stale under updates." Stated as a limitation, as in your notes.

**Argument skeleton** (one claim per paragraph, with source).

- Abstract: problem, gap, approach, the 8x/12x tail result, the sampling trade-off, the JOB runtime result. (Your numbers.)
- 1, P1: JOB 16b, PostgreSQL estimates 3,100 rows for a join with 7.4M; SkewSketch estimates 5.2M. (Your example.)
- 1, P2: The error compounds because each join's estimate feeds the next; Leis et al. show errors growing by orders of magnitude with joins. (Leis 2015; your ≥4-join statistic.)
- 1, P3: Why it is hard: accurate methods (sampling, learned models) pay at estimation or training time; the uniform assumption is cheap. (Your sampling numbers; Han 2022.)
- 1, P4: Key idea and result, with the limitation that sampling stays more accurate. Contributions list.
- 2: q-error definition; Count-Min and SpaceSaving in one paragraph each. (Your notes.)
- 3.1: Offline: chi-square test on a 1% sample, Count-Min over joint key values for correlated pairs, top 1,000 heavy hitters per column. (Your notes.)
- 3.2: Estimation: Eq. (1), why it helps on skewed keys, fallback. (Your notes; the reason it helps is arithmetic on Eq. (1), not a new claim.)
- 4: Extension, 2,400 lines of C, hook point. (Your notes.)
- 5.1: Setup. (Your notes; hardware and configuration missing.)
- 5.2: Accuracy, Table 1: SkewSketch between PostgreSQL and Sample1% on every statistic; largest gains at the tail. Then the ≥4-join statistic.
- 5.3: Cost, Table 2: overhead, build time, memory; end-to-end JOB runtime.
- 6: Related work by idea: compounding errors and benchmarks; sampling; learned estimators; sketch-based bounds.
- 7: Limitations: less accurate than sampling; correlated filter predicates; updates not evaluated.
- 8: Conclusion with the measured numbers.

**Dependency map.**

- q-error: defined in 2, used in Table 1, 5.2, 5.3 and the abstract.
- Correlated pair: defined in 3.1, used in Eq. (1), the fallback rule, the limitations.
- Heavy hitters, light keys: defined in 3.1, used in Eq. (1).
- Count-Min sketch: defined in 2, used in 3.1. Its role in Eq. (1) is not stated in your notes (question 1). If it has no role in the estimate, it should be cut or explained.
- SpaceSaving: defined in 2, used in 3.1.
- Eq. (1): defined in 3.2, used in the explanation of skew and in the 16b example.
- Table 1 (q-error): referenced in 5.2. Table 2 (cost): referenced in 5.3.
- JOB 16b: introduced in 1, returned to in 3.2 and 5.2.
- Sample1%: defined in 5.1, used in Tables 1 and 2 and in 6.

**Instances.** JOB 16b (cast_info ⋈ movie_keyword on movie_id). The ≥4-join statistic (60% vs 22%). Both tables of aggregates.

## Questions for the author

Method

1. What does the Count-Min sketch over "joint key values" supply to Eq. (1)? Are f_R(k) and f_S(k) Count-Min point queries for the keys SpaceSaving reports, or does SpaceSaving supply them? What are the sketch's width and depth?
2. What exactly is a "pair of join columns" in the correlation test: two join columns of the same table (e.g. cast_info.movie_id and cast_info.person_id), or the two sides of one join predicate? What contingency table does the chi-square test use (bucketed values?), and is the 1% sample uniform over rows?
3. In Eq. (1), is the heavy-hitter set H the union or the intersection of the two columns' top-1,000 lists? What is the uniform estimate for the light keys (e.g. |R_light|·|S_light| / max(d_R, d_S))?
4. Why chi-square at p < 0.01, a 1% sample and 1,000 heavy hitters? Were other values tried? Did you measure sensitivity to any of them? The draft has a `[TODO]` in Section 5 for this.
5. Your notes say PostgreSQL's estimator assumes join keys are independent and uniformly distributed. PostgreSQL's equi-join selectivity also matches most-common-value lists when both sides have them. Should the paper's description of the baseline be narrowed (e.g. "uniform beyond its most-common-value lists, and independent across joins")? Please confirm the wording you want.
6. How do estimates combine across a multi-join query: does each call to `set_joinrel_size_estimates` apply Eq. (1) to the join key between the new input and the joined relation, using base-table frequencies?

Evaluation

7. Hardware, PostgreSQL configuration (e.g. `work_mem`, parallelism, whether GEQO was off), and the data sizes of IMDb and STATS. The size of a 1% sample in MB is needed for Table 2 to compare storage.
8. How many JOB queries have ≥ 4 joins (the base for 60% and 22%)? Do you have the same statistic for Sample1% and for STATS-CEB?
9. Is there an end-to-end runtime for STATS-CEB? And is there a workload or query class where Sample1%'s 41 ms per query shows up in runtime? On JOB the two are within 2 s, so the cost argument currently rests on estimation latency and storage alone.
10. Did you consider comparing against a learned estimator or against pessimistic estimation (Cai et al.)? If not, should the paper say why (e.g. scope of a workshop paper)? I have not written a reason in the draft.
11. What was Sample1%'s estimate for JOB 16b? It would show where SkewSketch's remaining error stands.
12. Do the heavy keys explain the 16b error, i.e. does Eq. (1)'s heavy-hitter term account for most of SkewSketch's 5.2M estimate? The draft does not claim this.
13. Is the 31 s runtime gain concentrated in a few queries? A per-query breakdown or one plan change would give the runtime result a displayed instance.

References

14. The citation for index-based join sampling (the technique Sample1% implements) is missing.
15. Full entries (title, venue) for Cormode and Muthukrishnan 2005 and for Metwally, Agrawal and El Abbadi 2005.
16. Is there closer prior work on correlation-aware or skew-aware join estimation in PostgreSQL or elsewhere that the related work should position against? I have not searched.
17. Title, authors, affiliations and venue name.

## Notes on the draft

- Derived numbers: I computed ratios from your figures (95th-percentile q-error 340/41 ≈ 8x and 1,100/95 ≈ 12x; maximum 2.1e6/8.3e4 ≈ 25x and 4.5e7/3.1e5 ≈ 145x; 16b underestimate 7.4M/3,100 ≈ 2,400x and SkewSketch's q-error 7.4/5.2 ≈ 1.4; runtime 182 s to 151 s, a 17% reduction; overhead 41/0.4 ≈ 100x). Please check them.
- I did not set aside any rule of the skill.

## After review

I applied the review's findings to `after.md` with minimal edits, except as listed here.

Not applied:

- Finding 10 (the Count-Min sketch has no stated role in Eq. (1)): its fix depends on your answer to question 1. Either say in Section 3.2 which term of Eq. (1) reads the sketch, or cut the sketch from Sections 2 and 3.1. The existing `[TODO]` in Section 3.1 stays until then.

Applied with a small change from the proposed fix:

- Finding 11: after deleting the repeated sentence in Section 6, "SkewSketch has an offline cost too" no longer had anything for "too" to refer to. I changed it to "Like learned estimators, SkewSketch has an offline cost", which relies on the training-time point in Section 1.
- Finding 12: I left the abstract's description ("assuming that join keys are independent and uniformly distributed") in place, since it describes the assumption and does not name it. The name "uniformity assumption" is introduced in Section 1 and used everywhere after that.
- Finding 14: outside Section 5 I used "1% join sampling", because "Sample1%" is defined only in Section 5.1. In the conclusion I rearranged the sentence so it does not begin with "1%".

New questions:

18. Why does SkewSketch apply heavy-hitter estimation only to pairs that pass the chi-square test and leave every other join to PostgreSQL? Was this restriction for build time, for memory, or for accuracy on uncorrelated pairs? Is there a measurement, such as a variant that uses heavy hitters for every pair? (Marked in Section 3.1.) Until then, the conclusion credits the gain to SkewSketch as a whole, not to the restriction.
19. What does the chi-square test detect in a join-column pair, and why do pairs that pass it have keys that are frequent on both sides? The paper selects pairs by correlation, but its explanation of Eq. (1) rests on shared heavy keys. (Marked in Section 3.2.) I now say "correlated keys" throughout the paper, to match the title.
20. Han et al.'s finding that some learned estimators do not improve end-to-end runtime: was it on STATS-CEB in particular? Your notes give no benchmark, so I removed "on STATS-CEB" from Section 1.
21. Why do optimizers keep the uniformity assumption? The draft said it "persists because it is cheap". Your notes do not support that reason, so the text now says only that the assumption is cheap. If you have a source for the reason, I can put it back.
