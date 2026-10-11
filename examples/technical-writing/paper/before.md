# SkewSketch: Cheap Join Cardinality Estimation for Correlated Keys

## Abstract

Query optimizers such as PostgreSQL's estimate join sizes by assuming that join keys are independent and uniformly distributed. When join keys are skewed and correlated, this assumption fails, and the errors multiply as joins are stacked. We present SkewSketch, a lightweight estimator that targets this case. Offline, SkewSketch tests each pair of join columns in the workload's join graph for correlation. For the pairs that are correlated, it keeps a Count-Min sketch of the key values and tracks the 1,000 most frequent keys per column with SpaceSaving. At estimation time it computes the join size exactly over the heavy keys and uses the uniform estimate only for the remaining light keys. Uncorrelated pairs keep PostgreSQL's estimate. We implemented SkewSketch as a PostgreSQL 16 extension of about 2,400 lines of C. On JOB, it lowers the 95th-percentile q-error over all subplans from 340 to 41, and on STATS-CEB from 1,100 to 95. Total JOB runtime drops from 182 s to 151 s. Join sampling with a 1% sample is more accurate still, but it costs 41 ms per query to estimate, against 0.4 ms for SkewSketch. SkewSketch does not beat sampling on accuracy. It recovers most of sampling's runtime benefit for about one-hundredth of the estimation cost.

## 1 Introduction

Cardinality estimation remains the weakest part of cost-based query optimization. Leis et al. [1] showed that estimation errors in production optimizers grow by orders of magnitude as joins are added to a query, and that these errors lead to poor plans. A major cause is the textbook assumption that join keys are independent and uniformly distributed. Under that assumption, the size of a join on key `a` is estimated as

    |R ⋈ S| ≈ |R| · |S| / max(d_R, d_S),

where d_R and d_S are the numbers of distinct values of `a` in R and S. Real data seldom satisfies this assumption. In the IMDb data behind the Join Order Benchmark (JOB), a few popular movies account for a large share of the rows in both `cast_info` and `movie_keyword`. Joining these two tables on `movie_id` therefore produces far more rows than the uniform formula predicts, because the same keys are frequent on both sides. Each such join contributes its own error, and in a multi-way join the errors multiply.

The obvious remedies are expensive. Join sampling estimates correlated joins well, but it must run sample queries for every subplan the optimizer considers, at optimization time. Learned estimators can improve accuracy, but Han et al. [2] found that they require substantial training time and that some of them do not improve end-to-end runtime.

We ask a narrower question: how much of the benefit of an accurate estimator can be recovered at nearly the cost of the default one? Our answer is SkewSketch. Its central observation is that the error from correlated join keys is concentrated in a small number of heavy keys. If the optimizer knows the frequencies of those keys on both sides of the join, it can compute their contribution to the join size directly and leave only the light keys, where the uniformity assumption is more reasonable, to the default formula.

This paper makes the following contributions:

- SkewSketch, an estimator that applies sketches only to the join column pairs that a statistical test flags as correlated, and leaves all other joins to the existing estimator (Section 2).
- An implementation as a PostgreSQL 16 extension that requires no changes to the PostgreSQL source (Section 3).
- An evaluation on JOB and STATS-CEB against PostgreSQL 16 and 1% join sampling, covering subplan accuracy, end-to-end runtime, estimation overhead, build time, and memory (Section 4).

## 2 Method

SkewSketch has an offline phase, which builds statistics, and an online phase, which uses them during optimization.

### 2.1 Offline: selecting and summarizing correlated pairs

SkewSketch starts from the workload's join graph: the set of column pairs (R.a, S.b) that appear together in a join predicate. Building statistics for every pair would waste memory on joins that the default estimator already handles well, so SkewSketch first tests each pair for correlation. It draws a 1% sample and runs a chi-square test; it treats the pair as correlated if p < 0.01.

For each correlated pair, SkewSketch builds two structures:

- **A Count-Min sketch** [3] over the join key values. A Count-Min sketch answers frequency queries in fixed space, never underestimates a frequency, and overestimates it by a bounded amount with high probability.
- **A heavy-hitter list** for each column, holding the 1,000 most frequent keys, maintained with the SpaceSaving algorithm [4].

Pairs that fail the test receive no extra statistics.

### 2.2 Online: estimating a join

When the optimizer estimates the size of a join on a correlated pair, SkewSketch splits the key domain into heavy keys H, which are those in either column's heavy-hitter list, and light keys, which are all others. For key k, let f_R(k) and f_S(k) be its frequencies in R and S. The estimate is

    |R ⋈ S| ≈ Σ_{k ∈ H} f_R(k) · f_S(k)  +  U_light,

where the frequencies of heavy keys come from the sketches and U_light is the uniform estimate applied to the light keys only. That is, U_light is the formula from Section 1 with the rows and distinct values belonging to H removed from each side.

The first term is the join size restricted to the heavy keys, subject only to sketch error. This is where the uniform formula fails worst. If a key is frequent on both sides, its product f_R(k) · f_S(k) can far exceed the average contribution the uniform formula assigns to each key. The second term covers a long tail of keys whose frequencies are low and relatively even, which is the case the uniform formula was designed for.

For a join on an uncorrelated pair, SkewSketch returns PostgreSQL's own estimate unchanged.

## 3 Implementation

SkewSketch is a PostgreSQL 16 extension of about 2,400 lines of C. It hooks `set_joinrel_size_estimates`, the function that sets the row estimate for a join relation. When the join clause is on a pair that has SkewSketch statistics, the hook replaces the estimate with the one from Section 2.2; otherwise it defers to the standard code path. Because the hook sits at the level of join relations, SkewSketch is applied to every subplan the optimizer considers, not only to the final join. The statistics are built offline by a separate step and loaded by the extension.

## 4 Evaluation

### 4.1 Setup

**Benchmarks.** We use JOB [1], with 113 queries over the IMDb dataset, and STATS-CEB [2], with 146 queries.

**Metric.** For an estimate est and the true cardinality true, the q-error is max(est/true, true/est). A q-error of 1 is a perfect estimate, and the metric penalizes over- and underestimates symmetrically. We compute it for every subplan of every query, not only for the final result, because the optimizer's plan choice depends on the estimates for intermediate joins.

**Baselines.** (1) PostgreSQL 16's built-in estimator. (2) Sample1%, our own implementation of index-based join sampling with a 1% sample.

**Runtime measurement.** End-to-end runtime is the total over all JOB queries, taken as the median of three runs with a warm cache. The Sample1% runtime includes the time spent sampling during optimization.

### 4.2 Estimation accuracy

Table 1 reports the q-error over all subplans.

**Table 1.** q-error over all subplans (median / 95th percentile / max).

| Benchmark | PostgreSQL 16 | SkewSketch | Sample1% |
|---|---|---|---|
| JOB | 1.9 / 340 / 2.1e6 | 1.6 / 41 / 8.3e4 | 1.3 / 18 / 6.0e3 |
| STATS-CEB | 2.4 / 1,100 / 4.5e7 | 1.8 / 95 / 3.1e5 | 1.4 / 52 / 2.2e4 |

SkewSketch changes the median only modestly, from 1.9 to 1.6 on JOB and from 2.4 to 1.8 on STATS-CEB. This is expected: most subplans do not join on a correlated pair, and for those SkewSketch returns PostgreSQL's estimate. The improvement is in the tail. The 95th-percentile q-error falls by a factor of about 8 on JOB (340 to 41) and about 12 on STATS-CEB (1,100 to 95). The maximum falls by a factor of about 25 on JOB and about 145 on STATS-CEB.

Sample1% is more accurate than SkewSketch at every percentile on both benchmarks. Its 95th-percentile q-error is roughly half of SkewSketch's (18 against 41 on JOB, 52 against 95 on STATS-CEB), and its maximum is roughly an order of magnitude lower.

**Error by number of joins.** The default estimator's errors compound as joins are added. Among JOB queries with four or more joins, PostgreSQL misestimates the final join by more than 100x on 60% of the queries. SkewSketch does so on 22%.

**Example.** JOB query 16b joins `cast_info` and `movie_keyword` on `movie_id`. The true size of this join is 7.4M rows. PostgreSQL estimates 3,100 rows, an underestimate of about 2,400x. SkewSketch estimates 5.2M rows, a q-error of about 1.4. The error comes from popular movies that have both many cast entries and many keywords; the heavy-hitter term of Section 2.2 captures them directly.

### 4.3 End-to-end runtime

Better estimates matter only if they produce better plans. On JOB, total runtime is 182 s with PostgreSQL, 151 s with SkewSketch, and 153 s with Sample1%. SkewSketch reduces total runtime by 17%. Sample1% produces more accurate estimates but ends up 2 s slower overall, because its runtime includes the cost of sampling. We did not measure end-to-end runtime on STATS-CEB.

### 4.4 Cost

**Table 2.** Cost of each estimator.

| | SkewSketch | Sample1% |
|---|---|---|
| Estimation time per query (median) | 0.4 ms | 41 ms |
| Offline build time | 38 s (JOB), 21 s (STATS-CEB) | none |
| Space | 14 MB (JOB), 9 MB (STATS-CEB) | samples totaling 1% of the data |

SkewSketch's per-query estimation overhead is about 100 times lower than that of Sample1%, because it reads precomputed sketches instead of executing sample joins. It pays for this with an offline build of under a minute on both benchmarks. Its memory footprint is fixed by the sketch and heavy-hitter sizes and the number of correlated pairs, not by the size of the data; Sample1% must keep a sample proportional to the data.

## 5 Limitations

**Accuracy relative to sampling.** SkewSketch is less accurate than 1% join sampling on both benchmarks. Our claim is not that it is the most accurate estimator, but that it gives a better trade-off between accuracy and cost. If optimization time is not a constraint, sampling is the better choice.

**Filter predicates.** SkewSketch models correlation between join keys only. When a filter predicate is correlated with a join key, for example a filter that selects mostly popular movies, SkewSketch has no statistics for the filtered distribution and falls back to PostgreSQL's estimate.

**Updates.** Count-Min sketches and SpaceSaving both support incremental updates, but we have not evaluated sketch maintenance. All databases in our experiments were static. The accuracy of SkewSketch's statistics under inserts and deletes, and the cost of keeping them current, remain to be measured.

**Scope of the runtime result.** We report end-to-end runtime on JOB only.

## 6 Related Work

**Benchmarks and the scale of the problem.** Leis et al. [1] introduced JOB and showed that estimation errors grow by orders of magnitude as the number of joins increases. Han et al. [2] introduced STATS-CEB and compared a broad set of estimators. They found that learned estimators improve accuracy but require training time, and that some of them do not improve end-to-end runtime. Our results follow the same pattern for sampling: better estimates did not translate into faster total runtime once the cost of producing them was counted.

**Sketches.** SkewSketch builds on the Count-Min sketch [3] for frequency estimation and on SpaceSaving [4] for heavy-hitter tracking.

**Sketch-based bounds.** Cai et al. [5] also use sketches for join sizes, but they compute upper bounds rather than estimates. Pessimistic bounds make the optimizer robust against catastrophic underestimates, at the price of systematic overestimation. SkewSketch instead aims for a point estimate, and accepts that it can err in either direction.

## 7 Conclusion

Errors from correlated join keys are concentrated in a few heavy keys, and a small amount of targeted statistics is enough to remove much of that error. SkewSketch reduces tail q-error on JOB and STATS-CEB by one to two orders of magnitude relative to PostgreSQL 16, and cuts total JOB runtime by 17%, while adding 0.4 ms of estimation time per query and 9 to 14 MB of memory. Join sampling remains more accurate. The open questions are how to extend the approach to filter predicates that are correlated with join keys and how to maintain the sketches under updates.

## References

[1] V. Leis, A. Gubichev, A. Mirchev, P. Boncz, A. Kemper, and T. Neumann. How Good Are Query Optimizers, Really? PVLDB, 2015.

[2] Y. Han et al. Cardinality Estimation in DBMS: A Comprehensive Benchmark Evaluation. PVLDB, 2022.

[3] G. Cormode and S. Muthukrishnan. An Improved Data Stream Summary: The Count-Min Sketch and Its Applications. Journal of Algorithms, 2005.

[4] A. Metwally, D. Agrawal, and A. El Abbadi. Efficient Computation of Frequent and Top-k Elements in Data Streams. ICDT, 2005.

[5] W. Cai, M. Balazinska, and D. Suciu. Pessimistic Cardinality Estimation: Tighter Upper Bounds for Intermediate Join Cardinalities. SIGMOD, 2019.
