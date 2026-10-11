# Author's material: FKS perfect hashing lecture notes

Request: Write the lecture-notes section on FKS perfect hashing for an undergraduate algorithms course. Students know universal hashing, expectation and Markov's inequality. Markdown with LaTeX math.

Notes from the instructor:

- Goal: given a static set S of n keys from a universe U, build a table with O(n) space and O(1) worst-case lookup.
- Universal family H: for x ≠ y, Pr[h(x) = h(y)] ≤ 1/m.
- Lemma 1: with m = n², the expected number of colliding pairs is < 1/2, so Pr[no collision] > 1/2. But that uses n² space.
- Two levels: first level has m = n buckets; bucket i gets n_i keys. Bucket i gets a second-level table of size n_i² with its own h_i, re-drawn until collision-free.
- Lemma 2: E[Σ n_i²] < 2n. Proof: Σ n_i² = n + 2 · (number of colliding pairs), and E[number of colliding pairs] ≤ C(n,2)/m = (n − 1)/2 when m = n. So E[Σ n_i²] ≤ n + n − 1 < 2n.
- Markov: Pr[Σ n_i² ≥ 4n] < 1/2. So re-draw the first-level function until Σ n_i² < 4n; expected number of tries ≤ 2.
- Total space O(n): n first-level slots, plus Σ n_i² < 4n second-level slots, plus the hash functions (O(1) words each, n + 1 of them).
- Expected build time O(n).
- Questions students always ask: Why not just use m = n² directly? (Space.) Why n_i² and not n_i? (The second level must be collision-free, which Lemma 1 gives.)
- Reference: Fredman, Komlós and Szemerédi, "Storing a Sparse Table with O(1) Worst Case Access Time", JACM 1984.
