# Review: FKS perfect hashing (draft.md)

I checked the draft against material.md, the only source of facts. All numbers and bounds match the material or follow from it: E[C] ≤ (n−1)/(2n) < 1/2, E[C] ≤ (n−1)/2 for m = n, the split n_i² = n_i + 2·C(n_i, 2), E[Σ n_i²] < 2n, the Markov bound at 4n, the n + 1 hash functions and the O(n) build time. Both questions the material says students always ask are answered (the paragraph after Lemma 1, and the second paragraph of "Two levels"). The two `[TODO: ...]` markers, for the word-size and evaluation-time assumption and for the worked example, mark real gaps in the material and do not explain them in the prose. Findings follow, top-down.

## Substance

Substance, "Two levels", second paragraph, "Lemma 1 guarantees a likely collision-free function only when the range size is the square of the number of keys": a universal claim that neither Lemma 1 nor the material supports. Lemma 1 shows that a range of size n² is enough. It says nothing about smaller ranges, and the paragraph after Lemma 1 says only that the same calculation fails for m = n, not that no smaller range works. Fix: drop "only", and split the sentence: "The second level must have no collisions, because it is where a lookup ends. Lemma 1 guarantees a likely collision-free function when the range size is the square of the number of keys."

Substance, opening section, second paragraph, "The tool is the universal family from the previous section", and the TODO in the third paragraph ("with a reference to the universal-hashing section"): the material says that students know universal hashing. It does not say that these notes contain an earlier section on it. Fix: write "The tool is universal hashing." and ask the instructor whether a universal-hashing section exists to refer to, e.g. "[TODO: confirm there is a universal-hashing section to refer to]".

Substance, "Reference", [FKS84]: the entry is incomplete. It has no volume, issue or pages, and the first-name initials (M. L., J., E.) are not in the material. Fix: "[TODO: volume, issue and pages of the JACM article, and confirm the authors' initials]".

## Argument

Argument, proof of Lemma 1, "There are $\binom{n}{2}$ such pairs": "such pairs" points back to the previous sentence, which defines the colliding pairs, so the sentence reads as "there are C(n,2) colliding pairs". That is false, and it is not what the proof needs. Fix: "There are $\binom{n}{2}$ unordered pairs of distinct keys in $S$, and by universality each collides with probability at most $1/m = 1/n^2$."

Argument, "The construction and lookup", construction step 4 and lookup step 2: step 4 fills slot i only for buckets that have a table T_i, since steps 2 and 3 build one only for nonempty buckets. Lookup step 2 then tests "If $T_i$ is empty", and T_i does not exist for an empty bucket. The construction also never says where h is stored, though the space proof counts it. Fix: in step 4, add "for an empty bucket, mark slot $i$ empty; store $h$ alongside the array", and in lookup step 2 write "If slot $i$ is marked empty, report that $x \notin S$."

Argument, "The construction and lookup", last paragraph, "A lookup therefore evaluates two hash functions and makes one comparison, whatever $x$ is", repeated in the Theorem's proof: a lookup that lands in an empty bucket evaluates one hash function and makes no comparison. Fix: "at most two hash evaluations and one comparison" in both places.

## Design

Design: no findings. The section makes no design decisions; it is a construction with proofs.

## Math

Math, proof of Lemma 1, "The count $C$ is a nonnegative integer, so $h$ has a collision exactly when $C \ge 1$": the "so" gives the wrong reason. h has a collision when C ≥ 1 by the definition of C. Nonnegativity is what Markov's inequality needs, and integrality is what makes C ≠ 0 the same event as C ≥ 1. Fix: "The count $C$ is a nonnegative integer, so $C \ne 0$ means $C \ge 1$, and Markov's inequality applies:".

Math, "Two levels", first paragraph, "Write $S_i$ for the set of keys with $h(x) = i$", and the statement of Lemma 2, "the number of keys in $S$ with $h(x) = i$": x is never bound. Fix: "the set of keys $x \in S$ with $h(x) = i$" and "the number of keys $x \in S$ with $h(x) = i$".

## Sentences

Sentences: no findings beyond the sentence split given under Substance.
