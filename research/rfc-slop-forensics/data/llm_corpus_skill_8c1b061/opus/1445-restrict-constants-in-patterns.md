- Feature Name: `structural_match`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

# Summary

The current compiler gives pattern matching on constants a wider meaning than was intended. This RFC restricts that meaning without breaking much existing code, if any:

1. Add a feature-gated attribute `#[structural_match]`. Applied to a struct or enum `T`, it says that constants of type `T` may be used in patterns.
2. Have `#[derive(Eq)]` apply `#[structural_match]` automatically to the type it decorates. An attribute inserted by a derive does not require the feature gate.
3. When the compiler expands a constant of struct or enum type into an equivalent pattern, require that the type carries `#[structural_match]`. Constants of builtin types are always expanded.

In practice, these rules prevent a constant from being used in a pattern when its type defines equality by hand.

# Motivation

## How constants in patterns work today

A constant can appear in a pattern:

```rust
const ORIGIN: Point = Point { x: 0, y: 0 };

match p {
    ORIGIN => println!("at origin"),
    _ => println!("elsewhere"),
}
```

The compiler handles `ORIGIN` here by expanding it into the pattern `Point { x: 0, y: 0 }` and matching field by field. It never calls `PartialEq::eq`. For a type whose `PartialEq` is derived, the two approaches give the same answer, because derived equality also compares field by field.

## Where the two disagree

For a type with a hand-written `PartialEq`, the two approaches can give different answers. Consider a type that ignores one field in comparisons:

```rust
struct Tagged { value: u32, debug_label: &'static str }

impl PartialEq for Tagged {
    fn eq(&self, other: &Tagged) -> bool { self.value == other.value }
}

const ZERO: Tagged = Tagged { value: 0, debug_label: "zero" };

let t = Tagged { value: 0, debug_label: "computed" };
assert!(t == ZERO);          // true: eq ignores debug_label
match t { ZERO => {}, _ => panic!() }   // panics: the pattern compares debug_label
```

A reader who sees `ZERO` in a pattern will expect it to match what `== ZERO` matches. The current semantics break that expectation, and nothing in the program warns about it.

## Private fields

The expansion also exposes private structure. A constant of a type with private fields can be matched against, and the match compares those private fields. Changing the private representation of a type, while keeping its `PartialEq` behavior the same, can then change which values match a downstream crate's pattern. A library author has no way to prevent this today.

[TODO: say whether there are further motivations, for example soundness or the interaction with associated constants, and give any concrete bug reports.]

## Calling `PartialEq` instead

The direct fix would be to compile constant patterns into calls to `PartialEq::eq`. That would make the `Tagged` example behave as a reader expects. It would also change the meaning of existing code that relies on structural matching, and it would make exhaustiveness checking impossible for such patterns, since the compiler cannot reason about what a user-defined `eq` accepts. [TODO: confirm with the author whether this option was considered, and the reason it lost.]

This RFC instead keeps structural matching and restricts it to types where structural matching and `==` are known to agree.

# Detailed design

## The attribute

`#[structural_match]` may be placed on a struct or enum definition. It asserts that equality on the type is structural: two values are equal exactly when their fields (or their variant and fields) are equal. The attribute is feature-gated, because writing it by hand on a type with a custom `PartialEq` would make the assertion false.

## Derived equality implies the attribute

`#[derive(Eq)]` adds `#[structural_match]` to the type. The derived attribute does not require the feature gate, so stable code that derives `Eq` keeps the ability to use its constants in patterns.

[TODO: explain why the attribute follows `derive(Eq)` rather than `derive(PartialEq)`, or both. One consideration, to be confirmed: a type that derives only `PartialEq` may contain floating-point fields, whose `==` is not structural for NaN; but a type can also derive `Eq` while implementing `PartialEq` by hand, in which case equality is not structural either. The design needs to say how that case is handled.]

## The check

When the compiler expands a constant into a pattern, it checks the type of the constant:

1. If the type is a builtin type (integers, `bool`, `char`, `&str`, and references, tuples and arrays of these), the constant is expanded as today.
2. If the type is a struct or enum with `#[structural_match]`, the constant is expanded, and the check is applied recursively to each field.
3. Otherwise, the compiler reports an error at the pattern.

[TODO: confirm the exact list of builtin types. In particular, say whether floating-point constants remain allowed in patterns. Floats are builtin, so rule 1 admits them, but `==` on floats is not structural: `NAN != NAN`, and `0.0 == -0.0` although the two have different bit patterns.]

The recursive check matters for a struct that has the attribute but contains a field whose type does not. [TODO: confirm that the check recurses, rather than trusting the outer attribute.]

## Error message

The error names the constant, the type that lacks the attribute, and suggests either deriving `PartialEq` and `Eq` or replacing the pattern with a guard:

```rust
match t { x if x == ZERO => {}, _ => {} }
```

# Effect on existing code

The new check rejects a constant pattern only when the constant's type is a struct or enum that does not derive `Eq`. Code that uses constants of builtin types, or constants of types that derive `Eq`, is unaffected.

[TODO: give the evidence for "not much, if any" breakage, for example a crater run over published crates with the number of crates that fail. Without that number, the claim should be stated as an expectation, not a finding.]

[TODO: decide whether the check starts as a hard error or as a future-compatibility warning for one or more release cycles.]

# Drawbacks

The attribute ties a pattern-matching rule to a derive. A type whose author implements `Eq` by hand, with semantics that are in fact structural, loses the ability to use its constants in patterns unless the author adds `#[structural_match]`, which requires the feature gate. [TODO: say whether stabilizing the attribute is planned, or whether this restriction is accepted indefinitely.]

The rule is easy to state but adds a new concept, "structural match", that users meet only when they hit the error.

# Alternatives

[TODO: record the alternatives the author considered. Candidates to ask about, not to be presented as considered without confirmation:]

- [TODO: Compile constant patterns into `PartialEq::eq` calls, discussed under Motivation.]
- [TODO: Forbid constants of user-defined types in patterns entirely.]
- [TODO: Use a marker trait instead of an attribute, so that generic code can name the property.]

# Unresolved questions

1. Whether floating-point constants remain allowed in patterns.
2. How a type that derives `Eq` but implements `PartialEq` by hand is treated.
3. Whether the check starts as an error or a warning.
4. Whether `#[structural_match]` will ever be stable for hand-written use.
