- Feature Name: `structural_match`
- Start Date: 2016-01-06
- RFC PR: rust-lang/rfcs#1445
- Rust Issue: rust-lang/rust#31434

# Summary

The compiler currently accepts constants of almost any type inside patterns, and gives them a meaning that was never intended: it expands the constant into a pattern that compares the value field by field. This RFC narrows that behaviour without breaking existing code in practice:

- Introduce a feature-gated attribute `#[structural_match]`. Applied to a struct or enum `T`, it declares that constants of type `T` may be used in patterns.
- Make `#[derive(Eq)]` add `#[structural_match]` to the type it is applied to. Attributes inserted this way do not require the feature gate.
- When the compiler expands a constant of struct or enum type into a pattern, require that the type carry `#[structural_match]`. Constants of built-in types such as integers, `bool`, `char` and `&str` continue to be expanded as today.

The practical effect is that a constant may only be used in a pattern if its type uses derived, and therefore structural, equality.

# Motivation

Rust lets you write constants in patterns:

```rust
const ORIGIN: Point = Point { x: 0, y: 0 };

match p {
    ORIGIN => println!("at origin"),
    _ => println!("elsewhere"),
}
```

The compiler implements this by inlining the constant's value as a pattern, so the arm above is treated as `Point { x: 0, y: 0 }`. This is structural matching: it compares each field directly, never calling `PartialEq::eq`.

That works when `Point`'s equality is structural, which it is when `PartialEq` is derived. But nothing stops a type from defining equality differently:

```rust
struct CaseInsensitive(&'static str);

impl PartialEq for CaseInsensitive {
    fn eq(&self, other: &Self) -> bool {
        self.0.eq_ignore_ascii_case(other.0)
    }
}

const HELLO: CaseInsensitive = CaseInsensitive("hello");

match CaseInsensitive("HELLO") {
    HELLO => {}  // does not match!
    _ => {}
}
```

A reader would expect `HELLO` in a pattern to mean "equal to `HELLO`", and `==` says the two values are equal. But the pattern compares the string slices byte by byte and fails. The result is surprising and silent.

The deeper problem is that the current behaviour locks in an implementation detail. A type's author can change its `PartialEq` implementation, or change the private fields of the type, and silently alter which patterns match. Worse, the compiler sees through privacy: a constant of a type with private fields can be used in a pattern in another crate, exposing those fields' values to the matching logic. This breaks the abstraction boundary that privacy is meant to protect.

There are also soundness-adjacent concerns for future language features. Exhaustiveness checking assumes it knows the values a pattern matches. If we later want constants in patterns to call `PartialEq`, or to allow constants whose type has no structural notion of equality (such as floating-point types with NaN), we need to know which uses rely on structural semantics.

Rather than pick a final answer for every case now, this RFC stops the bleeding: it restricts constants in patterns to types whose authors have opted in to structural equality, keeping the door open for future designs.

# Detailed design

## The attribute

`#[structural_match]` may be placed on a struct or enum definition. It is feature-gated: user code that writes it directly needs `#![feature(structural_match)]`.

Its meaning is a promise from the type author: "equality of this type is structural, so expanding a constant of this type into a field-wise pattern gives the same result as calling `==`."

## Derive

`#[derive(Eq)]` emits `#[structural_match]` on the type along with the `Eq` impl. Because the attribute is produced by a built-in derive, the feature gate is not required.

The reason to hang this on `Eq` rather than `PartialEq` is that `Eq` signals a total, well-behaved equivalence relation. A type that derives both `PartialEq` and `Eq` almost certainly has structural equality in the sense we need. A type that derives only `PartialEq` might contain floats, where structural comparison and `==` disagree on NaN and signed zero.

In practice, derived `Eq` also requires derived (or at least present) `PartialEq`. A type that derives `Eq` while writing a custom `PartialEq` would satisfy the attribute check but break the promise; we accept this hole, since it requires an unusual combination and was already possible.

## Checking constants in patterns

When the compiler encounters a path in a pattern that resolves to a constant, it evaluates the constant and converts it to a pattern as today. During that conversion, whenever it encounters a value of struct or enum type `T`, it checks that `T` has `#[structural_match]`. If not, it reports an error:

```
error: to use a constant of type `CaseInsensitive` in a pattern,
       `CaseInsensitive` must be annotated with `#[derive(PartialEq, Eq)]`
```

The check is applied recursively: a constant of type `Wrapper(Inner)` requires both `Wrapper` and `Inner` to be structural-match types.

Constants of built-in types — integers, `char`, `bool`, `&str`, raw pointers, references to structural types, tuples and arrays of structural types — are always permitted, since their equality is structural.

Floating-point constants are still permitted for now, but a future-compatibility lint is added, because their structural matching disagrees with `==` for NaN.

## Interaction with generics

Constants are monomorphic, so the check happens on the concrete type. A generic `Option<T>` derives `Eq`, so it is structural-match; a constant `Option<CaseInsensitive>` fails because the inner type is not.

## Migration

Most types used as constants in patterns already derive `PartialEq` and `Eq`. For the remainder we roll this out as a warning in the first release, using the future-compatibility lint machinery, then turn it into an error after a crater run confirms impact is small.

# Drawbacks

- The rule ties pattern semantics to `derive`, which is a library-level mechanism. Types with hand-written but genuinely structural `Eq` impls cannot opt in on stable until the attribute is stabilized.
- The `derive(Eq)` but custom `PartialEq` loophole remains.
- It adds a second, invisible property that `derive(Eq)` controls, which users may not expect.

# Alternatives

**Call `PartialEq::eq` for constants in patterns.** This gives the "obvious" semantics, but breaks exhaustiveness checking, since the compiler can no longer reason about which values match. It would also make pattern matching run arbitrary user code.

**Forbid constants of user-defined types in patterns entirely.** This is cleaner but breaks a lot of real code that uses constant enum values or simple newtypes as patterns.

**Introduce a `StructuralEq` trait instead of an attribute.** A trait would be more composable and could be checked through generics. It is a larger design and can be added later; the attribute is an internal mechanism that could be reimplemented as a trait without user-visible change.

**Do nothing.** The privacy leak and the semantic mismatch would become harder to fix as more code depends on them.

# Unresolved questions

- What should the long-term story for floating-point constants in patterns be?
- Should the attribute eventually be stabilized, replaced by a trait, or kept as an implementation detail of `derive`?
- Should we close the custom-`PartialEq` loophole by also requiring `derive(PartialEq)`?
