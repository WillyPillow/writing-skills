# Rust RFC 1445: structural_match

- Feature Name: `structural_match`
- Start Date: [TODO: date]
- RFC PR: [TODO]
- Rust Issue: [TODO]

## Summary

The current compiler implements more expansive semantics for pattern matching than was originally intended. This RFC introduces mechanisms that rein in those semantics without breaking much, if any, existing code:

1. Introduce a feature-gated attribute `#[structural_match]`, which can be applied to a struct or enum `T` to indicate that constants of type `T` can be used within patterns.
2. Have `#[derive(Eq)]` apply this attribute automatically to the struct or enum it decorates. Attributes inserted automatically do not require the feature gate.
3. When the compiler expands a constant of struct or enum type into an equivalent pattern, require that the type carries `#[structural_match]`. Constants of builtin types are always expanded.

The practical effect is to prevent constants in patterns unless their type derives `Eq`. [TODO: the abstract is cut off at this point; confirm the rest of the summary.]

## Motivation

A constant of struct or enum type can appear in a pattern:

```rust
#[derive(PartialEq)]
struct Point { x: i32, y: i32 }

const ORIGIN: Point = Point { x: 0, y: 0 };

fn is_origin(p: Point) -> bool {
    match p {
        ORIGIN => true,
        _ => false,
    }
}
```

Today the compiler handles `ORIGIN` in the pattern by expanding it into the pattern `Point { x: 0, y: 0 }`. The match then compares the fields one by one. It never calls `PartialEq::eq`.

For `Point`, the two methods agree, because `PartialEq` is derived. They disagree as soon as a type defines its own `PartialEq`:

```rust
struct Caseless(&'static str);

impl PartialEq for Caseless {
    fn eq(&self, other: &Self) -> bool {
        self.0.eq_ignore_ascii_case(other.0)
    }
}

const HELLO: Caseless = Caseless("hello");

fn check(c: Caseless) -> (bool, bool) {
    let by_eq = c == HELLO;
    let by_match = match c { HELLO => true, _ => false };
    (by_eq, by_match)
}
```

For `Caseless("HELLO")`, `by_eq` is true and `by_match` is false. Two ways of asking "is this value `HELLO`?" give different answers, and nothing in the source of `check` warns the reader.

[TODO: confirm that the example above compiles and behaves as described on the current compiler. Matching on a string slice inside a constant may be handled differently from matching on integer fields; if so, replace the field type with one that shows the same effect.]

The abstract says that this behavior is more expansive than originally intended. [TODO: what the original intent was, and where it is recorded, such as an earlier RFC, a language reference entry or a design discussion, so that a reader can check that this RFC restores it rather than inventing a new rule.]

The behavior also constrains the language's future. If constants in patterns are defined by structural expansion, then changing a type's private fields can change which values match a public constant. If the language later wanted to define constant patterns in terms of `PartialEq` instead, existing matches could change meaning silently. [TODO: whether this future-compatibility concern is part of the author's motivation, and whether a specific planned feature depends on it.]

## Detailed design

### The attribute

`#[structural_match]` may be placed on a struct or enum definition. It asserts that, for this type, comparing two values field by field gives the same result as `==`. The compiler does not check that assertion. The attribute is behind a feature gate, so stable code cannot write it directly.

### Automatic application by `derive(Eq)`

When `#[derive(Eq)]` is applied to a struct or enum, the derive also inserts `#[structural_match]` on that type. An attribute inserted this way does not require the feature gate, so stable code that derives `Eq` gets the attribute.

The reason for tying the attribute to `Eq` rather than `PartialEq` is not stated in the abstract. [TODO: why `derive(Eq)` and not `derive(PartialEq)`. A plausible reason for the author to confirm is that it excludes types whose equality is not reflexive, such as types containing floats.] A type that derives `Eq` almost always derives `PartialEq` as well. If it derives `Eq` but implements `PartialEq` by hand, the attribute's assertion may be false. [TODO: whether `derive(Eq)` should insert the attribute only when `PartialEq` is also derived.]

### Expansion of constants

When the compiler expands a constant of struct or enum type `T` into a pattern, it checks that `T` carries `#[structural_match]`. If it does not, the program is rejected. [TODO: whether the check applies recursively, so that a `#[structural_match]` struct with a field of a type without the attribute is also rejected.]

Constants of builtin types, such as integers, characters, booleans, references and tuples of these, are always expanded. [TODO: confirm the exact list of builtin types, and say whether floating-point constants are included. Float patterns raise their own question, because `NaN` is not equal to itself, and the author may want to address it here or explicitly leave it out.]

### Diagnostics

[TODO: the error message for a rejected constant pattern, and the suggested fix in it, for example "add `#[derive(PartialEq, Eq)]` to `T`" or "use a guard: `x if x == CONST`".]

## Impact on existing code

The abstract claims that the change breaks "not much, if any" existing code. That is a compatibility claim, and it needs evidence. Code breaks if it uses, in a pattern, a constant whose type does not derive `Eq`, directly or through one of its fields.

[TODO: the evidence, for example a crater run over published crates, with the number of crates that fail to build and one or two representative cases. If no run has been done, narrow the claim to "code that uses only constants of types deriving `Eq` is unaffected."]

Code broken by this change can be fixed in one of two ways:

1. Derive `Eq` on the type, if its equality is structural.
2. Replace the constant pattern with a guard, `x if x == CONST`. That calls `PartialEq::eq`, which is what the writer most likely wanted.

[TODO: whether the change ships as a hard error, or as a warning first. A warning period would let the evidence above be gathered before the break.]

## Drawbacks

The attribute's assertion is not checked. A type can derive `Eq` while implementing `PartialEq` by hand, and its constants are then still expanded structurally. This RFC narrows the set of types where match and `==` can disagree, but it does not reduce that set to zero.

The rule ties a pattern-matching feature to a trait derive. A user who derives `Eq` for unrelated reasons, for example to use the type as a `HashMap` key, now also promises structural equality. A user who implements `Eq` by hand, even with structural semantics, cannot use constants of that type in patterns on stable without the feature gate.

## Alternatives

[TODO: the alternatives the author actually considered, each with the reason it lost. Suggestions for the author to evaluate, not yet considered:

1. Define constant patterns by calling `PartialEq::eq`. This makes match and `==` agree everywhere, but it gives up exhaustiveness checking for constants and changes the meaning of existing matches.
2. Keep the current behavior and document it.
3. Require a separate marker trait instead of an attribute, so that generic code could name it.]

## Unresolved questions

1. What the original intent was and where it is recorded (Motivation).
2. Why the attribute is tied to `Eq` rather than `PartialEq` (Automatic application by `derive(Eq)`).
3. Whether the check is recursive over fields (Expansion of constants).
4. How floating-point constants are treated (Expansion of constants).
5. How much existing code breaks, and whether there is a warning period (Impact on existing code).
