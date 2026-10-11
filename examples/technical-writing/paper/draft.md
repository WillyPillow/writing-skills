# SkewSketch: Join Cardinality Estimates for Correlated Keys at Sub-Millisecond Cost

[TODO: authors and affiliations]

## Abstract

Query optimizers such as PostgreSQL's estimate join sizes by assuming that join keys are independent and uniformly distributed. On correlated keys this assumption misestimates join sizes, and the errors multiply as joins are added. Sampling-based estimators correct much of this error but pay for it at estimation time. We present SkewSketch, which tests join-column pairs for correlation offline and, for correlated pairs only, estimates join size from the frequencies of each column's 1,000 most frequent keys. Implemented as a PostgreSQL 16 extension, SkewSketch reduces PostgreSQL's 95th-percentile q-error over all subplans from 340 to 41 on JOB and from 1,100 to 95 on STATS-CEB. It takes 0.4 ms per query to estimate, against 41 ms for 1% index-based join sampling, which remains more accurate (95th percentile 18 and 52). Total JOB runtime drops from 182 s to 151 s. SkewSketch thus trades some of sampling's accuracy for a hundredth of its estimation cost and a few megabytes of memory.

## 1 Introduction

In query 16b of the Join Order Benchmark (JOB), PostgreSQL 16 estimates that joining `cast_info` and `movie_keyword` on `movie_id` yields 3,100 rows. The join yields 7.4 million, so the estimate is low by a factor of about 2,400. PostgreSQL's estimator assumes that join keys are independent and uniformly distributed [TODO: confirm this description; PostgreSQL also matches most-common-value lists for equi-joins], and the key values of `movie_id` in these two tables are neither [TODO: confirm that skewed heavy keys cause the 16b error].

One misestimated join would cost little if the error stayed local. It does not: the estimate for one join is an input to the estimate for the next, so errors multiply. Leis et al. [1] showed on JOB that estimation errors grow by orders of magnitude as joins are added. In our measurements, PostgreSQL misestimates the final join by more than 100x on 60% of JOB queries with four or more joins.

The uniformity assumption persists because it is cheap. Methods that capture the data's real distribution pay at estimation time or before it. Index-based join sampling [TODO: citation] draws samples while the query is optimized; with a 1% sample, our implementation takes 41 ms per query at the median. Learned estimators improve accuracy but cost training time, and on STATS-CEB some of them do not improve end-to-end runtime [2]. The optimizer asks for an estimate for every candidate join, so an estimator that is to replace the default must correct the large errors without adding this cost.

SkewSketch targets joins on skewed keys, where a few keys that are frequent on both sides can account for most of the result. It tests each pair of join columns for correlation offline and, for the pairs that test as correlated, keeps the frequencies of each column's heavy hitters, its 1,000 most frequent keys. At estimation time it sums the products of the heavy hitters' frequencies, adds a uniform estimate for the remaining keys, and leaves every other join to PostgreSQL. On JOB 16b it estimates 5.2 million rows. SkewSketch does not match sampling's accuracy, and it does not yet handle filter predicates that are correlated with join keys or data that changes after the sketches are built.

This paper makes the following contributions:

- SkewSketch, a join cardinality estimator that applies heavy-hitter frequencies only to join-column pairs that a chi-square test finds correlated, and falls back to PostgreSQL's estimate elsewhere (Section 3).
- An implementation as a PostgreSQL 16 extension of about 2,400 lines of C (Section 4).
- An evaluation on JOB and STATS-CEB showing that SkewSketch cuts PostgreSQL 16's 95th-percentile q-error by 8x on JOB and 12x on STATS-CEB, and its maximum q-error by 25x and 145x. Its median estimation overhead is 0.4 ms per query, against 41 ms for 1% join sampling, which is more accurate on every reported statistic. Total JOB runtime falls by 17% (Section 5).

## 2 Preliminaries

**q-error.** For an estimate `est` of a true cardinality `true`, the q-error is max(est/true, true/est). It is at least 1, treats over- and underestimates symmetrically, and is 1 only for an exact estimate. We report it for every subplan of every query, not only for the final result, because the optimizer chooses each join based on the estimates of its inputs.

**Count-Min sketch.** The Count-Min sketch of Cormode and Muthukrishnan [3] summarizes the frequencies of items in a multiset in a fixed-size array of counters. It answers a point query for one item's frequency with an overestimate whose error is bounded in terms of the sketch's width and depth [TODO: check this description against [3]].

**SpaceSaving.** The SpaceSaving algorithm of Metwally, Agrawal and El Abbadi [4] tracks the most frequent items of a stream with a fixed number of counters [TODO: check this description against [4]]. We use it to find each column's heavy hitters.

## 3 SkewSketch

SkewSketch has an offline phase, which decides which join-column pairs need more than PostgreSQL's estimate and builds statistics for them, and an estimation phase, which runs inside the optimizer.

### 3.1 Offline phase

The offline phase starts from the workload's join graph. For each pair of join columns that appear together in it, SkewSketch tests for correlation with a chi-square test on a 1% sample of the data, at a significance level of p < 0.01 [TODO: define the pair and the contingency table; why these thresholds?]. We call a pair that passes the test a *correlated pair*.

For each correlated pair, SkewSketch keeps a Count-Min sketch over the joint key values [TODO: what the sketch supplies to Eq. (1); width and depth]. For each column, it tracks the 1,000 most frequent keys with SpaceSaving. We call these keys the column's *heavy hitters* and all other keys its *light keys*.

### 3.2 Estimation

Consider a join of relations R and S on a correlated pair, and let f_R(k) and f_S(k) be the frequencies of key k in the join columns of R and S. Let H be the set of heavy hitters [TODO: union or intersection of the two columns' heavy hitters?]. SkewSketch estimates the join size as

  |R ⋈ S| ≈ Σ_{k ∈ H} f_R(k) · f_S(k) + U_light,     (1)

where U_light is the uniform estimate for the light keys [TODO: give the formula for U_light].

The first term of Eq. (1) is exact for the keys in H, up to the error in their frequencies. The uniform assumption replaces each key's frequency with the column's average. When the same few keys are frequent in both R and S, their products f_R(k) · f_S(k) can exceed the uniform estimate for the whole join by orders of magnitude, and Eq. (1) counts them directly. Uniformity is assumed only for the light keys, whose frequencies are at most that of the least frequent heavy hitter [TODO: confirm, given SpaceSaving's approximation].

For a join on a pair that did not test as correlated, SkewSketch returns PostgreSQL's estimate unchanged. [TODO: state how Eq. (1) applies when R or S is itself a join, i.e. how estimates combine across a multi-join query.]

## 4 Implementation

SkewSketch is a PostgreSQL 16 extension of about 2,400 lines of C. It hooks `set_joinrel_size_estimates`, the function in which PostgreSQL's planner sets the estimated row count of a join relation. For a join whose key is a correlated pair, the hook replaces the row estimate with Eq. (1); for any other join it leaves PostgreSQL's estimate in place. The offline phase runs before the workload and stores the sketches for the hook to read [TODO: how the offline phase is invoked and where the sketches are stored]. Because the extension changes only cardinality estimates, the rest of the planner, including its cost model and join enumeration, is PostgreSQL's own.

## 5 Evaluation

The evaluation asks how much of PostgreSQL's estimation error SkewSketch removes, how it compares with join sampling on accuracy and on cost, and whether the accuracy gain reaches query runtime.

### 5.1 Setup

**Workloads.** We use JOB [1], 113 queries over the IMDb data set, and STATS-CEB [2], 146 queries. The databases are static: no updates run during or between measurements.

**Estimators.** We compare SkewSketch with two baselines. The first is PostgreSQL 16's own estimator. The second, *Sample1%*, is our implementation of index-based join sampling [TODO: citation] with a 1% sample.

**Metrics.** We report q-error over every subplan of every query, as the median, 95th percentile and maximum. End-to-end runtime is the total over all JOB queries, the median of three runs with a warm cache; for Sample1% it includes the time spent sampling. Estimation overhead is the median time per query spent in the estimator.

[TODO: hardware, PostgreSQL configuration, data set sizes.]

### 5.2 Accuracy

Table 1 gives q-error for the three estimators. On both benchmarks and on every statistic, SkewSketch is more accurate than PostgreSQL and less accurate than Sample1%.

Table 1: q-error over all subplans (median / 95th percentile / maximum).

| Benchmark | PostgreSQL 16 | SkewSketch | Sample1% |
|---|---|---|---|
| JOB | 1.9 / 340 / 2.1e6 | 1.6 / 41 / 8.3e4 | 1.3 / 18 / 6.0e3 |
| STATS-CEB | 2.4 / 1,100 / 4.5e7 | 1.8 / 95 / 3.1e5 | 1.4 / 52 / 2.2e4 |

SkewSketch's gains over PostgreSQL grow toward the tail of the distribution. At the median it lowers q-error from 1.9 to 1.6 on JOB and from 2.4 to 1.8 on STATS-CEB. At the 95th percentile it lowers it by 8x on JOB (340 to 41) and 12x on STATS-CEB (1,100 to 95), and at the maximum by 25x and 145x. This pattern fits the method: Eq. (1) changes the estimate only for joins on correlated pairs, and the uniform assumption fails worst on those joins [TODO: confirm that the subplans with the largest PostgreSQL errors are joins on correlated pairs]. Sample1% remains ahead at every statistic. Its 95th-percentile q-error is 2.3x lower than SkewSketch's on JOB (18 against 41) and 1.8x lower on STATS-CEB (52 against 95), and its maximum is about 14x lower on both.

The gain also holds on queries with many joins, where errors have the most room to compound. Among JOB queries with four or more joins [TODO: number of such queries], PostgreSQL misestimates the final join by more than 100x on 60% of them, and SkewSketch on 22%. In JOB 16b, the example from Section 1, PostgreSQL's estimate of 3,100 rows for the join of `cast_info` and `movie_keyword` on `movie_id` has a q-error of about 2,400 against the true 7.4 million rows; SkewSketch's estimate of 5.2 million has a q-error of 1.4 [TODO: Sample1%'s estimate for this join].

[TODO: sensitivity of accuracy to the number of heavy hitters, the Count-Min sketch size and the test's significance level, if measured.]

### 5.3 Cost

Table 2 sets SkewSketch's accuracy gain against what it costs.

Table 2: Cost of each estimator. Build time and memory are given for JOB / STATS-CEB.

| | PostgreSQL 16 | SkewSketch | Sample1% |
|---|---|---|---|
| Estimation overhead per query (median) | [TODO] | 0.4 ms | 41 ms |
| Build time | [TODO] | 38 s / 21 s | none |
| Memory or storage | [TODO] | 14 MB / 9 MB | 1% of the data [TODO: size in MB] |
| JOB total runtime | 182 s | 151 s | 153 s |

SkewSketch estimates about 100x faster than Sample1%, 0.4 ms against 41 ms per query at the median. It pays instead with an offline build of 38 s for JOB and 21 s for STATS-CEB and keeps 14 MB and 9 MB of sketches. Sample1% needs no build but keeps a 1% sample of the data.

On JOB, SkewSketch lowers total runtime from 182 s to 151 s, a 17% reduction. Sample1% reaches 153 s including its sampling time, so on JOB the two are within 2 s of each other, and Sample1%'s higher accuracy does not give it a faster total. JOB therefore does not separate the two estimators on runtime; the difference between them shows in estimation latency and memory. [TODO: STATS-CEB runtime; a query whose plan changes under SkewSketch, as a displayed instance of the runtime gain.]

## 6 Related Work

**Estimation errors in multi-join queries.** Leis et al. [1] introduced JOB and showed that the estimation errors of real optimizers grow by orders of magnitude as joins are added. Han et al. [2] introduced STATS-CEB in a benchmark study of cardinality estimators. SkewSketch addresses the error that both studies measure, and we evaluate it on both benchmarks.

**Sampling.** Index-based join sampling [TODO: citation] estimates join sizes from samples drawn at optimization time and is the most accurate estimator in our evaluation. SkewSketch moves the work offline: it builds its statistics once, before the workload, and estimates from them in 0.4 ms. It gives up part of sampling's accuracy in exchange (Section 5.2).

**Learned estimators.** Han et al. [2] found that learned estimators improve accuracy but cost training time, and that some of them do not improve end-to-end runtime. SkewSketch has an offline cost too, a build of 38 s for JOB and 21 s for STATS-CEB. Han et al.'s finding shows that a gain in q-error need not reach runtime; on JOB, SkewSketch's gain does (Section 5.3). We have not compared SkewSketch with a learned estimator [TODO: add a comparison, or state why it is out of scope].

**Sketches for join sizes.** Cai, Balazinska and Suciu [5] also use sketches, but compute upper bounds on join size rather than estimates. Their bounds are robust but overestimate. SkewSketch computes an estimate, so it can err in either direction, and it limits its sketches to correlated pairs. [TODO: closer prior work on skew- or correlation-aware join estimation, if any.]

## 7 Limitations

SkewSketch is less accurate than 1% join sampling on every statistic we report; its case rests on accuracy for the cost. It does not handle filter predicates that are correlated with join keys: for such queries it falls back to PostgreSQL's estimate [TODO: confirm that the fallback covers the whole join, not only the filter]. We have not evaluated sketch maintenance under updates, because the databases in our evaluation were static; how quickly the sketches go stale, and what keeping them current costs, are open.

## 8 Conclusion

On JOB and STATS-CEB, restricting heavy-hitter estimation to the join-column pairs that test as correlated removes most of PostgreSQL 16's tail error: the 95th-percentile q-error falls from 340 to 41 and from 1,100 to 95. It does so at 0.4 ms of estimation per query and 14 MB or less of memory, and it cuts total JOB runtime from 182 s to 151 s. Join sampling remains more accurate, at 41 ms per query and a 1% copy of the data. The next questions are whether SkewSketch's sketches can be kept current under updates and whether filter predicates correlated with join keys can be handled the same way.

## References

[1] Leis et al. How Good Are Query Optimizers, Really? VLDB, 2015. [TODO: full author list, volume and pages]

[2] Han et al. Cardinality Estimation in DBMS: A Comprehensive Benchmark Evaluation. VLDB, 2022. [TODO: full author list, volume and pages]

[3] Cormode and Muthukrishnan. [TODO: title and venue], 2005.

[4] Metwally, Agrawal and El Abbadi. [TODO: title and venue], 2005.

[5] Cai, Balazinska and Suciu. Pessimistic Cardinality Estimation. SIGMOD, 2019. [TODO: pages]

[TODO: reference for index-based join sampling]
