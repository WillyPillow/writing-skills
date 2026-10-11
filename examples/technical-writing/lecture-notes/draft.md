## FKS perfect hashing

Suppose the set of keys is fixed in advance: a set $S$ of $n$ keys drawn from a universe $U$, with no insertions or deletions. Our goal is a table that uses $O(n)$ space and answers every lookup "is $x$ in $S$?" in $O(1)$ time in the worst case, not only on average. The construction in this section achieves both. It is due to Fredman, Komlós and Szemerédi [FKS84]. It uses randomness only while building the table; once the table is built, every lookup does the same constant amount of work.

The tool is the universal family from the previous section. A family $H$ of functions from $U$ to $\{0, 1, \dots, m-1\}$ is *universal* if, for every pair of distinct keys $x \ne y$ in $U$, a function $h$ drawn uniformly at random from $H$ satisfies

$$
\Pr[h(x) = h(y)] \le \frac{1}{m}.
$$

We call $m$ the range size, and we will need universal families with range sizes $n^2$, $n$ and $n_i^2$ below. Each function in such a family takes $O(1)$ words to store. [TODO: state, with a reference to the universal-hashing section, the assumption that a key fits in $O(1)$ words and that evaluating $h \in H$ takes $O(1)$ time; the worst-case lookup bound depends on it.]

Two keys $x \ne y$ in $S$ *collide* under $h$ if $h(x) = h(y)$. If no two keys of $S$ collide, each key of $S$ gets its own slot in a table indexed by $h$. A lookup of $x$ then computes $h(x)$ and compares $x$ with the one key stored in that slot. Collisions are therefore what we must control.

### A collision-free table in quadratic space

The first question is how large the range must be before a random function from a universal family is likely to have no collisions on $S$ at all. A range of size $n^2$ is enough.

**Lemma 1.** Let $S$ be a set of $n$ keys, and let $h$ be drawn uniformly from a universal family with range size $m = n^2$. Then the expected number of colliding pairs in $S$ is less than $1/2$, and $h$ has no collisions on $S$ with probability greater than $1/2$.

*Proof.* Let $C$ be the number of unordered pairs $\{x, y\}$ of distinct keys in $S$ with $h(x) = h(y)$. There are $\binom{n}{2}$ such pairs, and by universality each collides with probability at most $1/m = 1/n^2$. Linearity of expectation gives

$$
\mathbb{E}[C] \le \binom{n}{2} \cdot \frac{1}{n^2} = \frac{n-1}{2n} < \frac{1}{2}.
$$

The count $C$ is a nonnegative integer, so $h$ has a collision exactly when $C \ge 1$. Markov's inequality bounds the probability of that event:

$$
\Pr[C \ge 1] \le \mathbb{E}[C] < \frac{1}{2}.
$$

Hence $\Pr[C = 0] > 1/2$. $\square$

Lemma 1 turns into an algorithm directly. Draw $h$, check it for collisions on $S$, and draw again if it has any. Each draw succeeds with probability greater than $1/2$, so the expected number of draws is less than 2. The resulting table answers every lookup with one hash evaluation and one comparison.

The trouble is the space. The table has $n^2$ slots to store $n$ keys, far from the $O(n)$ we want. Shrinking the range does not help on its own: with $m = n$, the same calculation gives only $\mathbb{E}[C] \le (n-1)/2$, which no longer shows that a collision-free function is likely.

### Two levels

The way out is to use the quadratic table only on small sets. A first-level function $h$ with range size $n$ splits $S$ into $n$ buckets. Write $S_i$ for the set of keys with $h(x) = i$, and $n_i = |S_i|$ for its size. The first level is allowed to have collisions: they only put several keys in the same bucket.

Each bucket $i$ then gets its own second-level table $T_i$ of size $n_i^2$, with its own function $h_i$ from a universal family with range size $n_i^2$. Why $n_i^2$ and not $n_i$? The second level must have no collisions, because it is where a lookup ends, and Lemma 1 guarantees a likely collision-free function only when the range size is the square of the number of keys. Applied to the $n_i$ keys of bucket $i$, Lemma 1 says that a random $h_i$ has no collisions on $S_i$ with probability greater than $1/2$.

The second-level tables take $\sum_i n_i^2$ slots in total, and this sum depends on how evenly $h$ spreads the keys. If $h$ sends every key to one bucket, the sum is $n^2$, and we are back to the quadratic table. If $h$ sends one key to each bucket, the sum is $n$. The next lemma shows that for a random first-level function the expected sum is less than $2n$.

[TODO: a small worked example from the instructor: a concrete $S$, a first-level $h$, the bucket sizes $n_i$, and the second-level tables.]

**Lemma 2.** Let $S$ be a set of $n$ keys, let $h$ be drawn uniformly from a universal family with range size $m = n$, and let $n_i$ be the number of keys in $S$ with $h(x) = i$. Then

$$
\mathbb{E}\Big[\sum_{i=0}^{n-1} n_i^2\Big] < 2n.
$$

*Proof.* The plan is to rewrite the sum of squares in terms of collisions, whose expected number universality bounds. Split each square as $n_i^2 = n_i + 2\binom{n_i}{2}$. Two distinct keys collide under $h$ exactly when they fall in the same bucket, so $\sum_i \binom{n_i}{2}$ is the number $C$ of colliding pairs in $S$. Since the buckets partition $S$, $\sum_i n_i = n$. Together,

$$
\sum_{i} n_i^2 = n + 2C.
$$

As in the proof of Lemma 1, each of the $\binom{n}{2}$ pairs collides with probability at most $1/m = 1/n$, so

$$
\mathbb{E}[C] \le \binom{n}{2} \cdot \frac{1}{n} = \frac{n-1}{2}.
$$

Taking expectations of the identity gives $\mathbb{E}[\sum_i n_i^2] \le n + (n - 1) < 2n$. $\square$

An expectation alone does not bound the space of the table we actually build, since a particular $h$ may be unlucky. Markov's inequality turns Lemma 2 into a bound that we can enforce by checking. The sum $\sum_i n_i^2$ is nonnegative, so

$$
\Pr\Big[\sum_i n_i^2 \ge 4n\Big] \le \frac{\mathbb{E}[\sum_i n_i^2]}{4n} < \frac{2n}{4n} = \frac{1}{2}.
$$

A random first-level function therefore satisfies $\sum_i n_i^2 < 4n$ with probability greater than $1/2$. If we draw $h$, compute the bucket sizes, and draw again whenever the sum is $4n$ or more, the expected number of draws is less than 2.

### The construction and lookup

The two lemmas give the whole construction. Steps 1 and 2 each draw a function and check it, and each check succeeds with probability greater than $1/2$.

1. Draw $h$ from a universal family with range size $n$. Compute the bucket sizes $n_0, \dots, n_{n-1}$. If $\sum_i n_i^2 \ge 4n$, draw $h$ again.
2. For each nonempty bucket $i$, draw $h_i$ from a universal family with range size $n_i^2$. If two keys of $S_i$ collide under $h_i$, draw $h_i$ again.
3. Store each key $x \in S_i$ in slot $h_i(x)$ of a table $T_i$ with $n_i^2$ slots.
4. In slot $i$ of a first-level array of $n$ slots, store $h_i$ and the location and size of $T_i$.

A lookup of a key $x \in U$ follows the same two levels:

1. Compute $i = h(x)$ and read slot $i$ of the first-level array.
2. If $T_i$ is empty, report that $x \notin S$.
3. Otherwise, compute $j = h_i(x)$ and compare $x$ with the key in slot $j$ of $T_i$. Report $x \in S$ if they are equal, and $x \notin S$ otherwise.

The comparison in step 3 is enough because $h_i$ has no collisions on $S_i$: if $x$ is in $S$, it is in $S_i$ and is stored in exactly slot $h_i(x)$ of $T_i$. A lookup therefore evaluates two hash functions and makes one comparison, whatever $x$ is. The randomness affected only which $h$ and $h_i$ the construction kept, not the work a lookup does.

### Space and time

**Theorem.** For a static set $S$ of $n$ keys, the construction above builds a table that uses $O(n)$ space and answers every lookup in $O(1)$ worst-case time. Its expected build time is $O(n)$.

*Proof.* The lookup bound was shown above: two hash evaluations and one comparison.

For space, the first-level array has $n$ slots. The second-level tables have $\sum_i n_i^2 < 4n$ slots in total, because step 1 keeps only a first-level function with that property. The table also stores at most $n + 1$ hash functions, $h$ and one $h_i$ per nonempty bucket, each in $O(1)$ words. The total is $O(n)$ words.

For build time, each draw in step 1 hashes the $n$ keys and sums the squares of the bucket sizes, which takes $O(n)$ time, and step 1 makes fewer than 2 draws in expectation. Each draw for bucket $i$ in step 2 sets up a table of $n_i^2$ slots and hashes the $n_i$ keys into it, which takes $O(n_i^2)$ time. By Lemma 1, bucket $i$ also needs fewer than 2 draws in expectation. Summed over the nonempty buckets, the expected time of step 2 is $O(\sum_i n_i^2) = O(n)$, again because $\sum_i n_i^2 < 4n$. Steps 3 and 4 take $O(n)$ time. $\square$

**Reference.** [FKS84] M. L. Fredman, J. Komlós and E. Szemerédi. Storing a Sparse Table with $O(1)$ Worst Case Access Time. *Journal of the ACM*, 1984.
