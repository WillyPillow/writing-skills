# RFC 2532: Associated Type Defaults, Revised

- Feature Name: `associated_type_defaults`
- Start Date: 2017-11-20
- Tracking Issue: (to be assigned)
- Status: Proposed

## Summary

This RFC revises the design of associated type defaults, which were first introduced in RFC 192. The revision changes the rules so that provided methods and other items in a trait may not assume that an associated type has its default value. The same restriction applies to the `default` keyword as it is used in specialization. Finally, the revision specifies that a trait object type, written `dyn Trait`, assumes the provided defaults and allows them to be elided in the type.

## Motivation

Associated types let a trait name a type that each implementation chooses. Associated type defaults extend this by allowing the trait to supply a fallback choice. An implementation that does not specify the associated type receives the default instead. This is convenient when most implementations agree on a type and only a few need something different.

The original design did not say clearly what could be assumed about a default. In particular, a provided method in a trait could be written in a way that relied on the associated type being the default, even though an implementation was free to override it. This produced code whose behavior depended on which implementation was selected, and the compiler had no consistent way to check this. The problem became more serious once specialization was considered, because specialization allows a more specific implementation to override a default that a general implementation has supplied.

The revision removes the ambiguity. A provided item may use the associated type only through its bounds, which are stated in the trait. It may not assume the concrete default. Because of this rule, every implementation can override the default without invalidating the provided items. The same logic governs specialization, where the `default` keyword marks an item that a more specific implementation may replace.

The change to trait objects follows from the same reasoning. A trait object has a fixed set of methods and a fixed associated type, so it is natural for the object type to use the defaults where the user has not written otherwise. Allowing `dyn Trait` to omit the defaults makes common code shorter without changing its meaning.

## Guide-level explanation

Consider a trait that describes a buffer. It has an associated type for the element, and a default element type is provided:

```rust
trait Buffer {
    type Item = u8;

    fn read(&self) -> Self::Item;
    fn describe(&self) -> &'static str {
        "a buffer"
    }
}
```

The provided method `describe` does not mention `Item`, so it is valid whatever type an implementation chooses. Under the revised rules, a provided method that wanted to use `Self::Item` as if it were `u8` would be rejected. The method would have to rely only on the bounds that the trait states, which for this trait are none.

Programmers who write implementations rarely notice the change. They may omit the associated type and use the default, or they may give their own type. Both are accepted, and both produce code that the compiler checks in the same way.

When a trait object is written, the compiler fills in the default for any associated type that the programmer has not specified. A value of type `dyn Buffer` therefore has a determined element type, without the programmer repeating it. The reference below gives the precise rule.

## Reference-level explanation

An associated type default is written in a trait with the form `type Name = Type;`. The default must satisfy the bounds that the trait places on the associated type. An implementation may omit the associated type, in which case the default is used, or it may provide its own type that also satisfies the bounds.

Provided items in a trait, including methods, constants, and other associated items with bodies, are checked under a restricted environment. Within such an item, the compiler does not use the default value of an associated type. The associated type is treated as an opaque type constrained only by the bounds in the trait. An attempt to rely on the concrete default produces an error that names the associated type and the provided item.

For specialization, an item marked `default` is subject to the same rule. A specializing implementation may replace the item, and any provided item that refers to the associated type must be valid for every possible replacement. The compiler checks this when the trait is declared, not when a particular implementation is selected.

A trait object type `dyn Trait` is well formed when every associated type of the trait without a default is specified, and the defaults are used for the rest. The object type may omit an associated type that has a default. The omitted type is filled in by the default at the point where the trait object is formed. If the trait has no defaults for some associated types, those must be written explicitly.

The rules above apply to traits in all editions. No change in the syntax of trait definitions is proposed beyond what is needed to express the new elision.

## Drawbacks

The restriction on provided items is stricter than what some users may expect, and it may require reworking code that depended on the old behavior. The rules are also more subtle than a simple default, and explaining them to newcomers takes effort. Some programmers may find the distinction between using a default and using a bound confusing at first.

The trait object elision adds a further rule that must be learned. It could surprise a programmer who expects every associated type to be written out, though the compiler error messages should make the situation clear.

## Rationale and alternatives

The main alternative is to keep the original rules and allow provided items to assume the default. This is simpler to state but unsound in the presence of specialization, and it allows behavior to change silently when an implementation overrides the default. Another alternative is to forbid defaults on associated types entirely. This would remove the problem but would also remove a useful feature that many traits rely on.

The proposed rules limit what provided items may assume, which keeps the feature usable and makes the behavior predictable. They also match the way that generic parameters are already checked, where a function may use only the bounds it declares.

The elision for trait objects was chosen because it follows the defaults that are already in the trait. It reduces repetition in common cases and does not introduce any new kind of type.

## Prior art

Other languages with associated types and defaults have faced similar questions about what a default may be assumed to mean. The general approach of limiting reasoning to declared bounds is common in those systems and has proven workable. The experience suggests that the restriction described here is the appropriate choice for a language that also has specialization.

## Unresolved questions

- Whether the restriction should be relaxed in cases where the associated type is marked as final or sealed, and if so how that marker would be expressed.
- The exact wording of the error messages for violations of the restriction.
- Whether elision should be allowed in type positions outside of trait objects, such as in bounds that name the trait.

## Future possibilities

A later revision could allow provided items to use defaults in a controlled way, for instance through an explicit annotation that the item depends on a particular default. Trait objects could gain other forms of elision as the rules for them mature. The specialization design may also take advantage of the clearer rules to allow more precise overrides. Each of these would require its own proposal and would be evaluated against the experience gained from the revised design.
