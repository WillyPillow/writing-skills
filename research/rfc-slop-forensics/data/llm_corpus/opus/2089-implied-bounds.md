- Feature Name: `implied_bounds`
- Start Date: 2017-07-28
- RFC PR: rust-lang/rfcs#2089
- Rust Issue: (none yet)

# Summary

Eliminate the need for "redundant" bounds on functions and impls when those bounds can be inferred from the input types and other trait bounds. Given

```rust
struct Set<K: Hash + Eq> { /* ... */ }
```

an impl such as

```rust
impl<K: Hash + Eq> Set<K> { /* ... */ }
```

could be written simply as

```rust
impl<K> Set<K> { /* ... */ }
```

because any well-formed `Set<K>` already implies `K: Hash + Eq`. Rust already supports implied bounds for lifetime relationships, supertraits, and projections. This RFC extends the mechanism to all where clauses on traits and types.

# Motivation

Bounds on type definitions are useful documentation and make invalid instantiations unrepresentable. Today they come with a cost: every impl and every function that mentions the type must repeat them. Consider a typical generic data structure:

```rust
pub struct HashMap<K: Hash + Eq, V, S: BuildHasher = RandomState> { /* ... */ }

impl<K: Hash + Eq, V, S: BuildHasher> HashMap<K, V, S> { /* ... */ }
impl<K: Hash + Eq, V, S: BuildHasher> Extend<(K, V)> for HashMap<K, V, S> { /* ... */ }
impl<K: Hash + Eq + Debug, V: Debug, S: BuildHasher> Debug for HashMap<K, V, S> { /* ... */ }

fn count_words<S: BuildHasher>(m: &HashMap<String, usize, S>) -> usize { /* ... */ }
```

The repetition is tedious, it obscures the bounds that actually matter (in the `Debug` impl, the interesting addition is `Debug`, not `Hash + Eq`), and it changes in lockstep: adding a bound to the struct forces edits to every impl. This is one reason the standard library deliberately avoids bounds on struct definitions, putting them only on impls instead. That is a reasonable workaround but it is a workaround: it means the type accepts nonsensical instantiations that can never be used.

Implied bounds already exist in a limited form. A function taking `&'a T` gets `T: 'a` for free. A function with `T: Ord` can use `T: PartialOrd` methods because of the supertrait relationship. Projections normalize using where clauses on the trait. Users regularly find the boundary between what is and is not implied surprising: why does `T: Ord` imply `T: PartialEq`, but `Set<T>` does not imply `T: Eq`?

# Guide-level explanation

If a type declares bounds on its parameters, those bounds are assumed to hold wherever the type appears in the signature of a function or the header of an impl.

```rust
struct Sorted<T: Ord>(Vec<T>);

impl<T> Sorted<T> {
    fn max(&self) -> Option<&T> {
        // Can call `Ord` methods on `T`: `Sorted<T>` implies `T: Ord`.
        self.0.last()
    }
}

fn merge<T>(a: Sorted<T>, b: Sorted<T>) -> Sorted<T> {
    // `T: Ord` is implied by the argument types.
    /* ... */
}
```

The same holds for traits. Where clauses on a trait — not only supertraits — are implied by the trait bound:

```rust
trait Graph where Self::Node: Hash + Eq {
    type Node;
    fn neighbors(&self, n: &Self::Node) -> Vec<Self::Node>;
}

fn reachable<G: Graph>(g: &G, start: G::Node) -> HashSet<G::Node> {
    // `G::Node: Hash + Eq` is implied by `G: Graph`.
    /* ... */
}
```

Callers are not relieved of anything. Someone calling `merge::<f64>` still gets an error, because `Sorted<f64>` is not a well-formed type. The bound has moved from the function signature to the type, where it is checked once.

# Reference-level explanation

## Well-formedness and implied bounds

We say a type is *well-formed* (WF) when all the where clauses on its definition hold. The compiler already checks that the types appearing in item signatures are WF. This RFC adds the inverse: inside an item, the WF-ness of the types in its signature is assumed, and the where clauses that WF-ness requires become available as hypotheses.

Concretely, for an item `I`:

- For a function, the input types are the argument types. The return type is not included (see below).
- For an impl, the input types are the self type and, for trait impls, the trait reference's type arguments.

For each input type `T`, `WF(T)` implies every where clause of `T`'s definition, recursively through components. For each trait reference `P: Trait<..>` in the where clauses, `WF(P: Trait<..>)` implies every where clause of `Trait`.

These implied clauses are added to the item's parameter environment, as if the user had written them.

## Callers must still prove WF

Soundness depends on callers being obligated to prove that the input types are well-formed. For functions, this means that at each call site the compiler checks `WF` of the instantiated argument types. For impls, it means that whenever the impl is used to satisfy an obligation, the self type and trait arguments must be WF.

The return type of a function is excluded because the callee produces it rather than receiving it. If return types contributed implied bounds, a function could claim `T: Trait` without anyone ever proving it.

## Interaction with existing implied bounds

The lifetime-based implied bounds and supertrait elaboration already in the compiler become special cases of this more general rule. Existing code continues to compile; no bound that is implied today stops being implied.

# Drawbacks

- **Removing a bound from a type becomes a breaking change in a new way.** Today, removing `T: Ord` from `struct Sorted<T: Ord>` only loosens requirements. With implied bounds, downstream impls that relied on the implied `T: Ord` stop compiling. Library authors will need to think of type-level bounds as part of their public API in both directions.
- **Less local reasoning.** Reading `impl<T> Sorted<T>` no longer tells you everything that is assumed about `T`. Tools like rustdoc can mitigate this by displaying implied bounds.
- **Implementation complexity.** Expanding implied bounds requires care to avoid cycles and exponential blow-up when types and traits refer to one another. The trait-system work under the Chalk effort provides a cleaner foundation for this, and the full feature may need to wait for it.

# Rationale and alternatives

**Status quo.** Keep requiring explicit bounds and continue recommending that libraries avoid bounds on type definitions. This is workable but leaves the inconsistency between supertraits and other where clauses in place.

**Opt-in implied bounds.** A marker on the type or trait could indicate that its bounds should be implied. This would avoid the new breaking-change hazard for existing libraries, at the cost of another concept to learn. Since existing types with bounds already force every user to repeat them, it is hard to see many cases where an author would want the bounds not to be implied.

**Imply only from impl headers, not functions.** This is a smaller step that captures much of the benefit. It is a reasonable fallback if the function case proves difficult to implement soundly.

# Unresolved questions

- How should implied bounds interact with trait objects and `impl Trait` in argument position?
- Should rustdoc show implied bounds by default?
- What is the right migration story for crates that want to remove a type-level bound after this lands?

# Future possibilities

Once implied bounds are available, it becomes reasonable for the standard library to reconsider placing bounds on types such as `HashMap` and `BTreeMap`. That would be its own discussion, but it is a direction this RFC makes possible.
