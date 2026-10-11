# Notes to the author: FKS perfect hashing section

You were not available before drafting, so I drafted the section from your notes. I marked the open gaps in the draft with `[TODO: ...]` and list them all below.

## Planning notes

**Reader.** An undergraduate in the algorithms course. They know universal hashing (the definition $\Pr[h(x)=h(y)] \le 1/m$), linearity of expectation and Markov's inequality. They have not seen a two-level table and may not expect that randomness can buy a worst-case guarantee.

**The point.** For a static set of $n$ keys, hashing twice gives $O(n)$ space and $O(1)$ worst-case lookup. The first level spreads the keys so that $\sum_i n_i^2 < 4n$. Each bucket then gets a collision-free table of size $n_i^2$. The claim is checkable: it fails if $\mathbb{E}[\sum_i n_i^2]$ is not $O(n)$, or if a collision-free second-level function cannot be found in $O(1)$ expected tries.

**The skeptic (here, the student).**

1. "Why not use one table with $m = n^2$?" Lemma 1 already gives a collision-free table that way, but it uses $n^2$ space. This is answered at the end of the Lemma 1 subsection, and it motivates the two levels.
2. "Why does bucket $i$ get $n_i^2$ slots and not $n_i$?" The second level must be collision-free, and Lemma 1 gives that only with quadratic size. This is answered where the second level is introduced.
3. "Doesn't $n_i^2$ blow the space back up to $n^2$?" It can, if every key lands in one bucket. Lemma 2 and the Markov step show that a first-level function with $\sum_i n_i^2 < 4n$ is found in fewer than 2 expected tries. This is answered by Lemma 2 and the corollary after it.

**Argument skeleton (one claim per paragraph, with its source).**

- Goal: static $S$, $|S| = n$, $O(n)$ space, $O(1)$ worst-case lookup. (Instructor notes, Goal.)
- Recall the universal family. (Notes, H.)
- With $m = n^2$, the expected number of colliding pairs is below $1/2$, so a random $h$ is collision-free with probability above $1/2$. (Notes, Lemma 1; the Markov step is mine but is the standard one.)
- That table uses $n^2$ space, which is the obstacle. (Notes, students' question 1.)
- Idea: hash to $n$ buckets and give each bucket a quadratic table, which Lemma 1 makes collision-free. (Notes, two levels; students' question 2.)
- The second-level space is $\sum_i n_i^2$, which lies between $n$ and $n^2$ depending on how the first level spreads the keys. (Derived from the definitions.)
- $\mathbb{E}[\sum_i n_i^2] < 2n$, via $\sum_i n_i^2 = n + 2\cdot(\text{colliding pairs})$. (Notes, Lemma 2.)
- Markov gives $\Pr[\sum_i n_i^2 \ge 4n] < 1/2$, so re-drawing takes fewer than 2 expected tries. (Notes, Markov.)
- Construction steps. (Notes, two levels and Markov.)
- Lookup: two hash evaluations and one comparison. (Derived from the construction.)
- Theorem: space is $O(n)$, lookup is $O(1)$ worst case, and expected build time is $O(n)$. (Notes, space and build time; the build-time argument is mine, see question 3.)
- Credit to Fredman, Komlós and Szemerédi. (Notes, reference.)

**Dependency map.**

- Universal family $H$: used in Lemma 1 (with $m = n^2$, and with $m = n_i^2$ per bucket) and Lemma 2 (with $m = n$).
- Lemma 1: used to motivate the two levels, to justify the size $n_i^2$, and to bound the expected second-level tries per bucket.
- Identity $\sum_i n_i^2 = n + 2C$: used only in the proof of Lemma 2.
- Lemma 2: used by the Markov step.
- Markov step (the corollary): used for the first-level re-draw loop, the space bound and the build time.
- Theorem: the payoff. Nothing after it in this section.
- Every object is used; nothing is cut.

**Instances.** The material has no worked example (no concrete $S$, hash function or bucket sizes). The only instances I used come from the definitions: the two extremes of $\sum_i n_i^2$ (all keys in one bucket gives $n^2$; one key per bucket gives $n$). I did not invent a numerical example. See question 2.

## Questions for the author

1. **Cost of evaluating a hash function.** The $O(1)$ lookup needs evaluating $h$ and $h_i$ to take $O(1)$ time, and a key to fit in $O(1)$ words. Your notes say each function takes $O(1)$ words to store but not how long it takes to evaluate. What does the earlier universal-hashing section assume, so I can refer to it? Marked `[TODO]` in the setup.
2. **Worked example.** Do you have a small example (a concrete $S$, a first-level $h$, the resulting bucket sizes and second-level tables) you would like in the notes? Students would benefit from one before Lemma 2. Marked `[TODO]` before the construction.
3. **Build-time argument.** Your notes state expected $O(n)$ build time without the argument. I wrote one: the first level takes fewer than 2 expected tries at $O(n)$ each; bucket $i$ takes fewer than 2 expected tries at $O(n_i^2)$ each (setting up a table of $n_i^2$ slots and hashing $n_i$ keys into it); and $\sum_i n_i^2 < 4n$. Please check that this matches how you present it in lecture, in particular that you charge $O(n_i^2)$ per try for initializing the table.
4. **Range sizes of $H$.** The construction needs a universal family for each range size $n$ and $n_i^2$. I wrote it as "a function from a universal family with range size $m$" each time. Is that how the earlier section phrases it (for example, a family $H_m$ for every $m$)?
5. **Empty buckets and the count of functions.** Your notes count $n + 1$ hash functions, which would give every bucket an $h_i$. A range of size $n_i^2 = 0$ makes no sense for an empty bucket, so the draft draws $h_i$ only for nonempty buckets, says the table stores *at most* $n + 1$ functions, and has lookup stop at an empty bucket. Is that how you want empty buckets handled?
6. **Contrast with chaining.** Students may ask how this differs from the chained table of the universal-hashing section, which gives $O(1)$ expected lookup. Your notes don't mention it, so I left it out. Do you want a sentence on it at the start?
7. **Fewer than 2 vs. at most 2 tries.** Your notes say the expected number of first-level tries is $\le 2$. Since each try succeeds with probability greater than $1/2$, the expectation is strictly less than 2, and I wrote "fewer than 2". Change it back if you prefer $\le 2$.
8. **Reference format.** I attributed the construction to Fredman, Komlós and Szemerédi (JACM 1984) in one sentence and a reference line. Tell me the course's citation style if it has one.

## After review

I applied every review finding except one.

- **Not applied: Math, proof of Lemma 1, "The count $C$ is a nonnegative integer, so $h$ has a collision exactly when $C \ge 1$."** The reviewer says the "so" gives the wrong reason. I think the sentence is correct as written: $h$ has a collision exactly when $C \ne 0$, and because $C$ is a nonnegative integer, $C \ne 0$ is the same event as $C \ge 1$. The next sentence then applies Markov's inequality to that event, and nonnegativity, which Markov needs, is already stated. The reviewer's proposed wording would drop the link between $C \ge 1$ and "$h$ has a collision", so I kept the original.

New questions:

1. **Earlier universal-hashing section.** Your request says students know universal hashing, but not that these notes have a section on it. I no longer say "from the previous section". Is there such a section, and should the word-size and evaluation-time assumption refer to it? (This replaces question 1 above about what that section assumes.)
2. **Reference details.** Your notes give the authors' surnames, the title, the journal and the year. The reference line now has a `[TODO]` for the volume, issue and pages, and for the authors' initials, which I took out because they were not in your notes.
3. **Empty buckets.** Construction step 4 now marks the first-level slot of an empty bucket as empty and stores $h$ alongside the array, and lookup step 2 tests that mark. The lookup bound now reads "at most two hash evaluations and one comparison", because a lookup that lands in an empty bucket stops after one. Please confirm this matches question 5 above.
