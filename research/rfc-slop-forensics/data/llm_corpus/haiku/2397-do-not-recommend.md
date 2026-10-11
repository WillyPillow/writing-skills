# Rust RFC 2397: `do_not_recommend`

- Feature Name: `do_not_recommend`
- Start Date: 2024-03-11
- Status: Proposed
- Language Team Sponsor: (none yet)

## Summary

This RFC adds a new attribute, `#[do_not_recommend]`, which may be placed on a trait implementation. When the trait solver fails to prove a goal, it sometimes searches for impls that would have been sufficient had some additional bound been satisfied, and it then suggests those bounds to the user. The attribute tells the compiler that a particular impl must never be offered as such a suggestion. The motivating example is the blanket implementation `impl<T: Iterator> IntoIterator for T`. With the attribute applied, a failure to prove `T: IntoIterator` produces a diagnostic that mentions only `IntoIterator`, and does not suggest that `Iterator` might need to be implemented.

## Motivation

Rust's diagnostics are most useful when they point at the thing the user actually needs to change. Trait errors are a common source of confusion, because the compiler sometimes reasons "transitively". Suppose a user writes a function with a bound `T: IntoIterator` and passes a type that does not implement it. The compiler looks at the impls that could apply. Among them is a blanket impl that applies to every type implementing `Iterator`. The compiler notices that this impl would apply if `T: Iterator` held, and it may then produce a note such as "perhaps `Iterator` should be implemented?" That note is accurate in a narrow technical sense, but for most users it is misleading. Implementing `Iterator` for the type would be a way to satisfy the blanket impl, yet the user may have no reason to want an iterator at all. The real question is why the type is not convertible into an iterator, and the note does not help answer it.

The problem gets worse as the number of blanket impls grows. Libraries commonly provide blanket impls such as `impl<T: Display> ToString for T` or `impl<T: Error> From<T> for Box<dyn Error>`. Each one creates a potential path for the compiler to suggest unrelated traits. Maintainers who write such impls currently have no way to tell the compiler that a particular impl is an implementation detail that should not appear in suggestions.

## Guide-level explanation

A maintainer may annotate a trait implementation with `#[do_not_recommend]`:

```rust
#[do_not_recommend]
impl<T: Iterator> IntoIterator for T {
    type Item = T::Item;
    type IntoIter = T;

    fn into_iter(self) -> T {
        self
    }
}
```

The attribute has no effect on whether the impl applies. A type that satisfies `T: Iterator` still implements `IntoIterator`, and code that relies on the impl continues to compile. The attribute affects only the diagnostic machinery. When the compiler reports an unsatisfied obligation, it will not describe this impl as a candidate whose where clauses the user might satisfy in order to make the obligation hold.

Users will normally never see the attribute. It is intended for library authors who know that a blanket impl is a convenience and not a meaningful signpost for end users.

## Reference-level explanation

The attribute is accepted only on trait implementations. Applying it to an inherent impl, a function, or a struct is an error. The attribute takes no arguments.

During error reporting for an unsatisfied trait obligation, the trait solver collects candidate impls whose headers unify with the obligation. For each candidate, the compiler may inspect its where clauses and report the first unsatisfied one as a suggestion. Under this RFC, a candidate marked with `#[do_not_recommend]` is excluded from this suggestion step. It is still considered when the solver decides whether an obligation holds, and it still participates in selection when the obligation is provable. The exclusion applies only to suggestions that name a further bound.

The exclusion is transitive in one direction only. If a `do_not_recommend` impl's where clause would have been the next step in a chain of suggestions, the chain stops at that impl. Other impls that are not marked remain eligible to be suggested, even if their own where clauses happen to be satisfied by the marked impl.

Incremental compilation and cross-crate metadata must record the attribute so that downstream crates see the same diagnostic behavior as the defining crate.

## Drawbacks

The attribute introduces a second mode in which a trait impl behaves differently from an unannotated impl, even though the two are equivalent for type checking. Some users may find it surprising that an impl can be real but unmentioned. There is also a risk that library authors apply the attribute too widely and hide impls that a user genuinely needs to know about. A diagnostic that omits a relevant suggestion can be as unhelpful as one that includes an irrelevant one.

## Rationale and alternatives

One alternative is to improve the heuristics that choose which candidate to report. The compiler already tries to filter suggestions, but heuristics cannot know the intent of the impl author. A blanket impl is recognizable by its shape, yet the shape alone does not say whether the impl is a convenience or a central part of the API. An explicit attribute gives the author direct control.

A second alternative is to suppress all suggestions involving blanket impls. This is too coarse. Some blanket impls, such as those for `Deref` forwarding, carry information the user should see. The attribute keeps the decision with the person who understands the impl.

A third alternative is to make the attribute a lint rather than a diagnostic rule. This RFC rejects that option, because the lint would not change the content of the emitted error, and users would still see the misleading note.

## Prior art

Other languages with trait-like features have faced similar tensions between full disclosure and readability in error messages. The Rust compiler already contains special handling for certain diagnostics that are judged unhelpful, and this RFC extends that practice in a controlled way.

## Unresolved questions

- Should the attribute be stabilized alongside a lint that warns when it is applied to an impl with no where clauses, since the attribute then has no effect?
- How should the attribute interact with the `on_unimplemented` attribute, which allows a trait author to customize the message for a specific trait?
- Is there a case in which the transitive exclusion described above hides a suggestion the user needs to resolve an error?

## Future possibilities

A future extension could allow the attribute to take a reason string that the compiler may display in verbose diagnostics. A more ambitious extension would let trait authors describe which bounds a blanket impl is meant to stand in for, so that diagnostics could phrase suggestions in terms of the user's own types. Either direction would build on the mechanism proposed here without changing its core behavior.
