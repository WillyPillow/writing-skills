# RFC: Restrict Constants in Patterns (structural_match)

- Feature Name: `structural_match`
- Start Date: 2015-12-01
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

The current compiler implements a more expansive semantics for pattern matching than was originally intended. This RFC introduces several mechanisms to reign in these semantics without actually breaking (much, if any) extant code:

- Introduce a feature-gated attribute `#[structural_match]` which can be applied to a struct or enum `T` to indicate that constants of type `T` can be used within patterns.
- Have `#[derive(Eq)]` automatically apply this attribute to the struct or enum that it decorates. **Automatically inserted attributes do not require use of feature-gate.**
- When expanding constants of struct or enum type into equivalent patterns, require that the struct or enum type is decorated with `#[structural_match]`. Constants of builtin types are always expanded.

The practical effect of these changes will be to prevent the use of constants in patterns unless the type of those constants is either a built-in type (like `i32` or `&str`) or a user-defined constant whose type has opted in to structural matching by deriving `Eq`.

## Motivation

### What constants in patterns do today

Rust allows a path naming a constant to appear in a pattern:

```rust
const ORIGIN: Point = Point { x: 0, y: 0 };

match p {
    ORIGIN => println!("at origin"),
    _ => println!("elsewhere"),
}
```

The compiler handles this by *expanding* the constant: it evaluates `ORIGIN`, obtains `Point { x: 0, y: 0 }`, and treats the pattern as though the programmer had written `Point { x: 0, y: 0 }`. Matching then proceeds structurally: the scrutinee is compared field by field.

The documentation and the original intent describe a different rule, which is that matching a constant against a value uses `==`, that is, the `PartialEq` implementation of the constant's type. In the common case the two coincide. Where a type defines a custom `PartialEq`, they may not.

### The problem

Consider a type with a hand-written equality:

```rust
struct CaseInsensitive(String);

impl PartialEq for CaseInsensitive {
    fn eq(&self, other: &Self) -> bool {
        self.0.to_lowercase() == other.0.to_lowercase()
    }
}

const HELLO: CaseInsensitive = CaseInsensitive(String::new()); // illustrative
```

A programmer reading `match x { HELLO => ... }` would reasonably expect that the arm is taken whenever `x == HELLO`, so that `"HELLO"` and `"hello"` both match. The compiler instead compares the underlying fields, with strict structural equality, ignoring the `PartialEq` implementation entirely. This is a silent mismatch between what the code says and what it does.

There are more severe cases:

- A type whose `PartialEq` is not reflexive, for example a floating-point wrapper with NaN semantics. Structural matching could say two values are equal that `==` says are different, or the reverse.
- A type containing private fields. Pattern expansion of a constant exposes the private structure of a type across module boundaries, which breaks encapsulation. A library author who changes the private representation could change which values a constant pattern matches in downstream crates.
- A type with interior mutability, whose structural content may be meaningless.

More generally, the current behavior is a hazard for the future: if the language ever wants to guarantee that matching against a constant means `==`, or to let such matching be compiled into an efficient decision tree, the existing semantics get in the way. We would like to settle on a rule that is simple to state, safe, and consistent with where we want the language to go.

## Detailed design

### The `structural_match` attribute

We introduce an attribute, `#[structural_match]`, which may be applied to a struct or enum definition. Its meaning is:

> Constants whose type is this type may appear in patterns, and the result of matching against such a constant is exactly equal to the result of an `==` comparison with the constant.

The attribute is a *promise* by the type's author. In particular, the author promises that the derived-equals notion of equality (field-by-field comparison) agrees with the type's `PartialEq` and `Eq` implementations, so that expansion and `==` are indistinguishable.

The attribute is feature-gated, so that on stable Rust users cannot apply it directly. It is intended as an implementation detail of `#[derive(Eq)]` for now.

### Automatic application via `derive(Eq)`

`#[derive(Eq)]` is the natural trigger. A type that derives `Eq` is stating that its equality is an equivalence relation. When combined with `#[derive(PartialEq)]`, the derived equality is structural by definition, so expansion is faithful.

Therefore, we modify the `Eq` derive so that it emits `#[structural_match]` on the item. Because the attribute is inserted by the compiler's own deriving machinery, it does not trip the feature gate.

A user who writes `PartialEq` by hand and then derives `Eq` could still trigger this. To handle that, the derive for `Eq` should additionally require, in a later check, that `PartialEq` is also derived, but this requirement is left as an open question and is not enforced in this RFC.

### Checking at constant expansion

When the compiler expands a constant into a pattern, it examines the constant's type:

1. If the type is a built-in type (integers, floating point, `bool`, `char`, `&str`, tuples, arrays, references to these, and so on), expansion proceeds as today. We call these types *structurally matchable* by construction.
2. If the type is a struct or enum, check for `#[structural_match]`. If present, expansion proceeds. If absent, the compiler reports an error.
3. For compound types, the check applies recursively to each field type that is visited during expansion.

The new error looks like:

```
error: to use a constant of type `CaseInsensitive` in a pattern,
       `CaseInsensitive` must be annotated with `#[derive(PartialEq, Eq)]`
```

### Transition

To limit breakage, the first release issues a *warning* in situations that would be errors, via the usual lint mechanism with `deny` as eventual default. A crater run on the then-current ecosystem found a small number of cases, nearly all of which derive neither `PartialEq` nor `Eq` but happen to use constants in patterns, and in which adding the derive is a trivial fix.

## Drawbacks

- Some code that works today will stop compiling, though we estimate the amount to be tiny. Typical fixes: add `#[derive(PartialEq, Eq)]` to the type.
- Types from other crates that implement `PartialEq` by hand cannot be used as pattern constants, even if their authors would be willing to promise structural equivalence, because the attribute is unstable. Such authors will need to wait for stabilization of a mechanism.
- Attaching meaning to `derive(Eq)` makes that derive do slightly more than its name suggests. This is a minor concern; it is an implementation mechanism.
- Floating-point constants in patterns are already special. This RFC leaves them alone.

## Alternatives

**Do nothing.** The semantic gap would persist, and any later change would be more disruptive.

**Make constants in patterns always use `PartialEq::eq`.** This matches the documentation but is incompatible with exhaustiveness checking and efficient compilation, since `eq` is arbitrary code. It would also be a larger behavior change for existing programs.

**Require the author to opt in explicitly with a stable attribute.** Perhaps the cleanest long-term, but it adds surface area to the language and requires an accompanying RFC. The feature gate retains the option.

**Check only that `PartialEq` is derived.** A type can be `PartialEq` without being `Eq`, which would allow floats-containing types, with their non-reflexive equality, to participate. Requiring `Eq` is safer.

**Forbid constants of user-defined types in patterns entirely.** Too restrictive; enum-valued constants are commonly used.

## Unresolved questions

- Should the check require `PartialEq` to be derived as well, rather than hand-written?
- When, if ever, should the attribute be stabilized, and under what name?
- Should the error be a hard error immediately for types defined in the same crate as the pattern?
