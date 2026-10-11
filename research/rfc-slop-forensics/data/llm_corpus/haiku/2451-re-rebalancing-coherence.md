# RFC 2451: Re-Rebalancing Coherence

- Feature Name: `re_rebalancing_coherence`
- Start Date: 2017-10-02
- Tracking Issue: (to be assigned)
- Status: Proposed

## Summary

This RFC clarifies an ambiguity in RFC 1023, which governs when a trait implementation is permitted under the orphan rules. It extends the rules so that type parameters may appear in the self type of the implementation, regardless of whether a local type appears before them in the trait's parameter list. In concrete terms, it allows the implementation `impl<T> ForeignTrait<LocalType> for ForeignType<T>`, which the current rules reject in some situations.

## Motivation

Rust's coherence rules exist to guarantee that for any type and trait there is at most one implementation that applies. The orphan rule is the main tool for this. It says that an implementation may be written only in the crate that defines the trait or in the crate that defines one of the types appearing in the implementation, and the rules specify which types count and in what order they must appear.

RFC 1023 introduced a rebalancing of these rules. It made the position of local types matter, so that a local type appearing before any uncovered type parameter would allow the implementation. The intent was to permit common patterns while keeping the uniqueness guarantee. However, the text left open how type parameters that are not covered by a local type should be handled, and the result is that some implementations which seem safe are rejected, while others that are accepted depend on the order of parameters in a way that is hard to explain.

The case considered here is a common one. A crate defines a type, and wants to implement a trait from another crate for a generic container of a foreign type, with the trait parameterized by the local type. The implementation is unambiguous, because the local type appears in the trait's argument, and the generic parameter appears only inside the foreign container. Under the existing wording, the compiler's reasoning about which parameter is covered is unclear, and the implementation is not accepted in every case where it should be.

Clarifying the rules would remove a source of confusion and would let crates express these implementations directly, rather than through wrapper types that add runtime or ergonomic cost.

## Guide-level explanation

An implementation of a trait is written as an `impl` block that names the trait and the self type. The orphan rules ask whether the crate is allowed to write that block. Under the proposed clarification, a type parameter may appear in the self type, as long as the implementation is anchored to a local type in the trait's argument list.

Here is an example:

```rust
// In crate `mine`, which defines `Local`.
struct Local;

// `ForeignTrait` and `ForeignType` come from another crate.
impl<T> ForeignTrait<Local> for ForeignType<T> {
    // ...
}
```

The implementation is accepted because `Local` appears in the trait's parameters. The type `T` is covered by `ForeignType`, which is foreign, but the coverage rule permits the implementation since the local type anchors it. A programmer who reads the code would expect this to be fine, and under the clarified rules it is.

The change does not allow implementations that would overlap with other implementations. The rules that prevent overlap remain as they were. A programmer who tries to write an implementation that two different crates could both provide will still receive an error, and the diagnostic will explain which rule was violated.

## Reference-level explanation

The orphan check considers the trait reference, consisting of the trait and its parameters, and the self type. Types are classified as local or foreign, and type parameters are classified as covered or uncovered. A type parameter is covered when it appears inside a type constructor that is not a type parameter itself. An uncovered type parameter appears directly as a type argument of the trait reference or as the self type.

Under RFC 1023, an implementation is permitted when, for the sequence of types in the trait reference followed by the self type, a local type appears before any uncovered type parameter. This rule is retained. The clarification adds the following: a type parameter that appears only inside a foreign type constructor in the self type is not counted as uncovered for the purpose of this ordering, provided a local type appears earlier in the trait reference.

In the example above, the trait reference is `ForeignTrait<Local>`, and the self type is `ForeignType<T>`. The local type `Local` appears first. The parameter `T` is covered by `ForeignType`, so it does not count as uncovered. The implementation satisfies the rule.

The compiler must check the overlap condition as before. The orphan rule is a necessary condition for permitting an implementation, but not a sufficient one. Overlap checking continues to determine whether two implementations can apply to the same types.

Where the local type appears only after an uncovered parameter, the implementation remains rejected. This preserves the ordering rule from RFC 1023 for cases that the ordering was designed to address.

The change affects only the orphan check. It does not alter method resolution, type inference, or the treatment of blanket implementations in other crates.

## Drawbacks

The clarified rule adds one more case that programmers must understand, and it makes the orphan check slightly harder to explain. The interaction between covered and uncovered parameters and the ordering of local types is subtle, and newcomers may find the rule surprising. There is also a risk that the more permissive rule will allow implementations that a future change to the trait would break, since the orphan check is only as stable as the trait it governs.

## Rationale and alternatives

The alternative is to leave RFC 1023 unchanged and rely on wrapper types. This works but adds boilerplate and sometimes runtime overhead. Another alternative is to remove the ordering requirement entirely, but that would reintroduce the risk of overlapping implementations across crates, which the ordering was designed to prevent.

The proposed clarification keeps the ordering rule and changes only how a covered parameter is classified. This makes the change narrow. It also matches the intuition behind the original design, which was that a local type anchors an implementation and that foreign type constructors do not, by themselves, make an implementation ambiguous.

## Prior art

Coherence rules in other languages with trait-like features have faced similar tradeoffs between permissiveness and the guarantee of unique implementations. Those systems typically choose a rule based on which crate owns a type or a trait, and then restrict the cases in which a foreign implementation can be written. The rule proposed here follows that pattern, with the refinement needed for Rust's parameter ordering.

## Unresolved questions

- Whether the clarified rule should be extended to cover cases where the local type appears inside a foreign type constructor in the trait reference.
- How the rule interacts with fundamental types such as references and boxes, which have special treatment in the orphan check.
- Whether the diagnostic for rejected implementations should suggest the wrapper-type workaround explicitly.

## Future possibilities

A future RFC could revisit the ordering rule as a whole, in light of more experience with the clarified version. It could also consider whether certain foreign types should be treated as fundamental for the purpose of the orphan check, which would widen the set of permitted implementations further. Any such change would need its own analysis of overlap and of stability across crate versions.
