# RFC 1445: structural_match

- Feature Name: `structural_match`
- Start Date: [TODO]
- RFC PR: [TODO]
- Rust Issue: [TODO]

## Summary

The current compiler implements a more expansive semantics for pattern matching than was originally intended. This RFC adds mechanisms to narrow that semantics while breaking little or no existing code. [TODO: the author's basis for "little or no"; see Drawbacks.]

1. Add a feature-gated attribute `#[structural_match]`. Applied to a struct or enum `T`, it indicates that constants of type `T` can be used in patterns.
2. Make `#[derive(Eq)]` apply this attribute automatically to the struct or enum it decorates. An automatically inserted attribute does not require the feature gate.
3. When the compiler expands a constant of struct or enum type into an equivalent pattern, require that the type carries `#[structural_match]`. Constants of builtin types are always expanded.

The practical effect is to prevent the use of constants in patterns when the constant's type does not derive `Eq`. [TODO: the abstract is cut off after "prevent the use of constants in"; the author must supply the end of the sentence.]

## Motivation

A pattern in a `match` can name a constant. The compiler treats that as a request to expand the constant into the pattern its value would spell out, and to match field by field. For a constant of a user-defined type, this expansion ignores any custom equality the type defines. The match compares structure, while `==` on the same type may compare something else.

Take a type whose `PartialEq` implementation ignores one field:

```rust
struct Tagged { id: u32, note: &'static str }
// PartialEq compares only `id`.
const T: Tagged = Tagged { id: 1, note: "a" };

match x {
    T => { /* ... */ }
    _ => { /* ... */ }
}
```

Under the expanded semantics the arm matches only values whose `id` is 1 and whose `note` is `"a"`. A reader who knows that `==` ignores `note` expects the arm to match a value with `id` 1 and any note. The two readings disagree, and the compiler picks the structural one without saying so. [TODO: the author's own example or a bug report. This one is constructed to show the mismatch and is not drawn from the material.]

The abstract says this reach is more than was "originally intended". [TODO: the author's statement of what the original intent was, and where it was recorded. Do not leave this as a bare assertion: a reviewer will ask who intended what.]

The central design question follows. Which types may appear as constants in patterns? A rule that is too loose lets types with custom equality through. A rule that is too strict breaks working programs. The RFC takes the position that a type is eligible when it opts in with `#[structural_match]`, and that `#[derive(Eq)]` is the usual way of opting in.

## Detailed design

### The attribute

`#[structural_match]` may be written on a struct or enum. It is feature-gated, so only code that enables the gate can write it by hand. The attribute asserts that matching on the type's structure agrees with comparison by equality. [TODO: author to say whether the compiler checks the assertion or takes it on trust. A check would need the type's `PartialEq` to be derived, and the abstract does not say.]

### Automatic application

`#[derive(Eq)]` inserts the attribute on the type. The inserted attribute does not need the gate. Stable code that derives `Eq` therefore gains the attribute without the author writing it.

The reason to hang the attribute on `Eq` is that deriving `Eq` is an existing statement by the programmer that equality on the type is a structural, total relation. [TODO: author to confirm this is the reasoning. The abstract specifies the mechanism and gives no explanation of the choice. Also say whether `derive(PartialEq)` alone was weighed, since a type that derives only `PartialEq` is not covered.]

### Expansion

When the compiler expands a constant of struct or enum type into a pattern, it checks for the attribute on that type. If the type lacks it, the compiler reports an error. [TODO: the error kind, and whether the first release uses a warning. The abstract says the changes aim to avoid breakage, which suggests a warning period, but does not say so.]

Constants of builtin types, such as integers, are always expanded. Builtin types have no user-defined equality that could disagree with their structure. [TODO: list the builtin types covered, in particular whether references, tuples, arrays, and floating-point numbers count. Floating-point values need care, since their `==` is not reflexive for NaN, and the abstract does not say how they are handled.]

### Nested types

A constant may contain fields whose types are themselves user-defined. [TODO: state whether the check applies recursively, so that a struct deriving `Eq` with a field of non-`structural_match` type still fails when expanded. The abstract says nothing about nesting.]

## Drawbacks

Some existing programs use constants of types without `derive(Eq)` in patterns. Those programs stop compiling, or start warning, once the rule applies. The RFC's aim is that few or none do, but the material gives no count. [TODO: a measurement, such as a crater-style run over a corpus of published crates, or a statement that none was done.]

The workaround for an affected program is to add `#[derive(Eq)]` where it is valid, or to rewrite the arm with a guard that uses `==`. [TODO: confirm the guard form is acceptable to the author and show the rewritten code.]

A feature-gated attribute adds a name to the compiler's surface that stable code cannot write. The RFC accepts that cost in exchange for not freezing a user-visible attribute before its design settles. [TODO: author to confirm this was the reason for the gate.]

## Alternatives

[TODO: the material records no alternative. Questions for the author: was a stable attribute preferred, was the check tied to `PartialEq` instead of `Eq`, and was a deprecation lint without an error considered? List an alternative here only after the author confirms it was weighed.]

Not changing anything is a valid option and is the baseline. It leaves the surprising matching semantics in the compiler. The RFC counts that as the reason to act.

## Unresolved questions

1. The end of the sentence on the "practical effect".
2. Whether the check is recursive.
3. How floating-point constants are treated.
4. Whether the first release warns or errors.
5. The size of the set of programs the change affects.
