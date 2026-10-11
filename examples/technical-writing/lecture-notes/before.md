# FKS Perfect Hashing

## The problem

Ordinary hashing with chaining gives $O(1)$ *expected* lookup time. Some unlucky keys can still collide, so a single lookup may take longer. In this section we ask for more, in a restricted setting.

**Static dictionary problem.** We are given a set $S$ of $n$ keys from a universe $U$. The set never changes: no insertions, no deletions. We want a data structure that

- uses $O(n)$ space, and
- answers "is $x \in S$?" in $O(1)$ time in the **worst case**, for every query $x \in U$.

We may use randomness while *building* the structure, and the build time only needs to be good in expectation. Once the structure is built, every lookup is guaranteed fast.

The solution below is due to Fredman, Komlós and Szemerédi (1984), and is usually called **FKS hashing** or **two-level perfect hashing**. A hash function is *perfect* for $S$ if it causes no collisions among the keys of $S$.

## Background: universal hashing

Recall that a family $\mathcal{H}$ of functions $h : U \to \{0, 1, \dots, m-1\}$ is **universal** if for every pair of distinct keys $x \neq y$,

$$
\Pr_{h \in \mathcal{H}}\bigl[h(x) = h(y)\bigr] \le \frac{1}{m},
$$

where $h$ is drawn uniformly at random from $\mathcal{H}$. We will use a family in which each function is described by $O(1)$ machine words and can be evaluated in $O(1)$ time, for example $h_{a,b}(x) = ((ax + b) \bmod p) \bmod m$ for a prime $p > |U|$. We need such a family for every table size $m$ we use.

Throughout, for a hash function $h$ and the key set $S$, let

$$
C = \#\bigl\{\{x, y\} \subseteq S : x \neq y,\ h(x) = h(y)\bigr\}
$$

be the number of **colliding pairs**. There are $\binom{n}{2}$ pairs, each colliding with probability at most $1/m$, so by linearity of expectation

$$
\mathbb{E}[C] \le \binom{n}{2} \cdot \frac{1}{m}. \tag{1}
$$

## Step 1: a quadratic-size table has no collisions

**Lemma 1.** Let $h$ be drawn from a universal family with $m = n^2$. Then $\Pr[h \text{ has no collisions on } S] > 1/2$.

*Proof.* By (1),

$$
\mathbb{E}[C] \le \binom{n}{2} \cdot \frac{1}{n^2} = \frac{n(n-1)}{2n^2} < \frac{1}{2}.
$$

$C$ is a non-negative integer, so by Markov's inequality, $\Pr[C \ge 1] \le \mathbb{E}[C] < 1/2$. Hence $\Pr[C = 0] > 1/2$. $\blacksquare$

This already solves the lookup problem: draw $h$, check whether it has collisions on $S$, and re-draw if it does. Each attempt succeeds with probability more than $1/2$, so the expected number of attempts is less than $2$. With a collision-free $h$, store each key $x$ in slot $h(x)$, and answer a query $x$ by comparing it with the single key in slot $h(x)$.

The catch is space: the table has $n^2$ slots. For a million keys that is $10^{12}$ slots. We want $O(n)$.

## Step 2: two levels

The idea is to use the quadratic-size trick only on small groups of keys.

**First level.** Draw $h$ from a universal family into a table of $m = n$ buckets. Bucket $i$ receives the keys
$$
S_i = \{x \in S : h(x) = i\}, \qquad n_i = |S_i|.
$$
The buckets may contain collisions; that is fine.

**Second level.** For each bucket $i$, build a separate table $T_i$ of size $m_i = n_i^2$, with its own hash function $h_i$ drawn from a universal family into $\{0, \dots, n_i^2 - 1\}$. Re-draw $h_i$ until it has no collisions on $S_i$. By Lemma 1 (applied with $n_i$ in place of $n$), each attempt succeeds with probability more than $1/2$. Store each $x \in S_i$ in slot $T_i[h_i(x)]$.

(Buckets with $n_i = 0$ get an empty table; buckets with $n_i = 1$ get a table of size 1, and any $h_i$ works.)

**Lookup.** To check whether $x \in S$:

1. Compute $i = h(x)$.
2. Compute $j = h_i(x)$.
3. Return whether $T_i[j] = x$.

This is two hash evaluations and one comparison, so it takes $O(1)$ time in the worst case, regardless of $x$ and regardless of which hash functions were drawn.

The remaining question is space. The second-level tables use $\sum_i n_i^2$ slots in total. If one bucket received all $n$ keys, this would be $n^2$ again. We need to show that a random first-level function makes $\sum_i n_i^2$ linear in $n$, at least with good probability.

## Step 3: the second level is small on average

**Lemma 2.** If the first-level function $h$ is drawn from a universal family with $m = n$, then
$$
\mathbb{E}\Bigl[\sum_{i=0}^{n-1} n_i^2\Bigr] < 2n.
$$

*Proof.* First we count. For any integer $k \ge 0$,
$$
k^2 = k + 2\binom{k}{2},
$$
and $\binom{n_i}{2}$ is the number of colliding pairs inside bucket $i$. Every colliding pair lies in exactly one bucket, so summing over all buckets gives
$$
\sum_i n_i^2 = \sum_i n_i + 2\sum_i \binom{n_i}{2} = n + 2C.
$$
Now take expectations and use (1) with $m = n$:
$$
\mathbb{E}[C] \le \binom{n}{2}\cdot\frac{1}{n} = \frac{n-1}{2}.
$$
Therefore
$$
\mathbb{E}\Bigl[\sum_i n_i^2\Bigr] = n + 2\,\mathbb{E}[C] \le n + (n - 1) < 2n. \qquad \blacksquare
$$

Lemma 2 bounds the expectation, but we want a guarantee for the structure we actually build. Markov's inequality turns the expectation bound into a probability bound. Since $\sum_i n_i^2 \ge 0$,
$$
\Pr\Bigl[\sum_i n_i^2 \ge 4n\Bigr] \le \frac{\mathbb{E}\bigl[\sum_i n_i^2\bigr]}{4n} < \frac{2n}{4n} = \frac{1}{2}.
$$

So we modify the first level: **draw $h$, compute the bucket sizes $n_i$, and re-draw $h$ until $\sum_i n_i^2 < 4n$.** Each attempt succeeds with probability more than $1/2$, so the expected number of attempts is less than $2$.

## The complete construction

**Build($S$):**

1. Repeat: draw $h : U \to \{0, \dots, n-1\}$ from a universal family and compute $n_0, \dots, n_{n-1}$; until $\sum_i n_i^2 < 4n$.
2. For each bucket $i$ with $n_i > 0$:
   repeat: draw $h_i : U \to \{0, \dots, n_i^2 - 1\}$ from a universal family; until $h_i$ has no collisions on $S_i$.
   Store each $x \in S_i$ in $T_i[h_i(x)]$.
3. Store $h$, an array of $n$ entries where entry $i$ holds $h_i$ and a pointer to $T_i$, and the tables $T_i$.

**Lookup($x$):** $i \gets h(x)$; $j \gets h_i(x)$; return $T_i[j] = x$.

## Analysis

**Lookup time.** $O(1)$ in the worst case, as shown above.

**Space.** The structure consists of

- the first-level array: $n$ entries;
- the second-level tables: $\sum_i n_i^2 < 4n$ slots in total, guaranteed by step 1;
- the hash functions: $n + 1$ of them ($h$ and one $h_i$ per bucket), each $O(1)$ words.

The total is $O(n)$ words. This is a worst-case bound on the final structure, not just an expected one, because step 1 does not stop until the bound holds.

**Build time.** One attempt in step 1 costs $O(n)$: hash every key and add up the squares of the bucket sizes. The expected number of attempts is less than $2$, so step 1 takes $O(n)$ expected time.

For bucket $i$ in step 2, one attempt costs $O(n_i)$ to hash the keys of $S_i$ and check for collisions, plus allocating a table of $n_i^2$ slots. By Lemma 1 the expected number of attempts is less than $2$. Summing over buckets, step 2 takes expected time
$$
O\Bigl(\sum_i (n_i + n_i^2)\Bigr) = O(n + 4n) = O(n).
$$

So the whole structure is built in $O(n)$ expected time.

**Theorem (Fredman, Komlós, Szemerédi).** A static set of $n$ keys can be stored in $O(n)$ space so that membership queries take $O(1)$ worst-case time. The structure can be built in $O(n)$ expected time.

## Common questions

**Why not use a single table with $m = n^2$?** It works for lookups (Lemma 1), but it uses $\Theta(n^2)$ space. The point of the two-level scheme is to pay quadratic space only within each bucket, where the buckets are small, and Lemma 2 shows the quadratic costs add up to $O(n)$.

**Why does bucket $i$ get $n_i^2$ slots and not $n_i$?** The second level must be collision-free, since that is what makes lookups $O(1)$ in the worst case: there is exactly one key to compare against. Lemma 1 guarantees a collision-free function with good probability only when the table has size (at least) the square of the number of keys. With only $n_i$ slots, a random function would usually have collisions, and we would be back to chaining.

**Why is it fine that the first level has collisions?** The first level only has to split $S$ into groups whose squared sizes add up to $O(n)$. Collisions there are resolved by the second level.

**Where does randomness enter the guarantees?** Only in the build time. Once the structure is built, the space is less than $n + 4n$ slots plus the hash functions, and each lookup is two hash evaluations and one comparison, no matter what.

## Reference

M. L. Fredman, J. Komlós and E. Szemerédi. Storing a Sparse Table with $O(1)$ Worst Case Access Time. *Journal of the ACM* 31(3):538–544, 1984.
