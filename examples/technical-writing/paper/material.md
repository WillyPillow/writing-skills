# Author's material: SkewSketch workshop paper

Request: Write a 4-page workshop paper (Markdown is fine) from these notes, for a database workshop.

Idea: SkewSketch. Cardinality estimators in optimizers such as PostgreSQL's assume join keys are independent and uniformly distributed. On correlated keys, errors multiply across joins.

Method:

- Offline: for each pair of join columns that appear together in the workload's join graph, test for correlation (chi-square on a 1% sample, p < 0.01). Keep a Count-Min sketch over the joint key values, for correlated pairs only.
- Heavy hitters: top 1,000 keys per column, tracked with SpaceSaving.
- At estimation time, for a join on a correlated key pair: estimated size = sum over heavy hitters k of f_R(k) · f_S(k), plus the uniform estimate for the remaining (light) keys.
- Uncorrelated pairs fall back to PostgreSQL's estimate.

Implementation: a PostgreSQL 16 extension, about 2,400 lines of C, hooking `set_joinrel_size_estimates`.

Evaluation:

- Benchmarks: JOB (113 queries, IMDb) and STATS-CEB (146 queries).
- Metric: q-error = max(est/true, true/est), over every subplan.
- Baselines: PostgreSQL 16's estimator; Sample1%, our own implementation of index-based join sampling with a 1% sample.
- q-error, median / 95th percentile / max, over all subplans:
  - JOB: PostgreSQL 1.9 / 340 / 2.1e6; SkewSketch 1.6 / 41 / 8.3e4; Sample1% 1.3 / 18 / 6.0e3
  - STATS-CEB: PostgreSQL 2.4 / 1,100 / 4.5e7; SkewSketch 1.8 / 95 / 3.1e5; Sample1% 1.4 / 52 / 2.2e4
- End-to-end JOB runtime, total over all queries, median of 3 runs, warm cache: PostgreSQL 182 s; SkewSketch 151 s; Sample1% 153 s (including the time spent sampling).
- Estimation overhead per query, median: SkewSketch 0.4 ms; Sample1% 41 ms.
- Build time: SkewSketch 38 s (JOB), 21 s (STATS-CEB). Sample1% needs no build but keeps the samples: 1% of the data.
- Memory: SkewSketch 14 MB (JOB), 9 MB (STATS-CEB).
- By number of joins: among JOB queries with ≥ 4 joins, PostgreSQL misestimates the final join by more than 100x on 60% of them; SkewSketch on 22%.
- Example, JOB 16b: cast_info ⋈ movie_keyword on movie_id. PostgreSQL estimate 3,100 rows, true 7.4M, SkewSketch estimate 5.2M.

Weaknesses: less accurate than sampling; the point is accuracy for the cost. Doesn't handle filter predicates correlated with join keys (falls back to PostgreSQL). Sketch maintenance under updates not evaluated; the databases were static.

Related work (my notes):

- Leis et al. 2015, "How Good Are Query Optimizers, Really?" (VLDB): introduced JOB; showed estimation errors grow by orders of magnitude as joins are added.
- Han et al. 2022, "Cardinality Estimation in DBMS: A Comprehensive Benchmark Evaluation" (VLDB): introduced STATS-CEB; learned estimators improve accuracy but cost training time, and some don't improve end-to-end runtime.
- Cormode and Muthukrishnan 2005: Count-Min sketch.
- Metwally, Agrawal and El Abbadi 2005: SpaceSaving.
- Cai, Balazinska and Suciu 2019, "Pessimistic Cardinality Estimation" (SIGMOD): uses sketches to compute upper bounds on join size rather than estimates; robust, but overestimates.
