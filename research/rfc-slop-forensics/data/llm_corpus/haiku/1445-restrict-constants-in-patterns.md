# RFC 1445: Restricting Constants in Patterns with `#[structural_match]`

- Feature Name: `structural_match`
- Start Date: 2016-01-20
- Status: Proposed

## Summary

This RFC narrows the rules under which a constant may be used as a pattern. The current compiler accepts a constant of any struct or enum type in a pattern, and it expands the constant's value into a pattern by inspecting the value's structure. This behavior is broader than the language designers originally intended, and it creates several problems, including surprising results when the type's equality implementation differs from its structure. The proposal introduces an attribute, `#[structural_match]`, that marks the types whose constants may be used in patterns. The attribute is applied automatically to types that derive `Eq`, so that most code is unaffected, and types that do not opt in receive a clear error when their constants are used in a pattern.

## Motivation

A pattern in Rust compares a value against a structure that describes what the value should look like. When a constant appears in a pattern, the compiler replaces it with a pattern that matches the constant's value. For primitive types such as integers and characters, this is straightforward. For structs and enums, the compiler must look inside the constant and produce a pattern for each field, which relies on the assumption that matching the pattern is equivalent to checking equality.

That assumption does not always hold. A type may implement `PartialEq` in a way that ignores some fields, or that compares them by some other rule. When a constant of such a type is used in a pattern, the match follows the structural rule rather than the equality the author wrote. The two can disagree, and the program's behavior can then depend on a detail the programmer did not expect.

The compiler currently allows this for all struct and enum types. The authors of the language want to limit the use of constants in patterns to types for which structural matching agrees with the equality that the programmer has defined. The proposal makes this a requirement, and it does so without breaking most existing programs.

## Guide-level explanation

A constant can appear in a pattern only if its type is marked with `#[structural_match]`. The attribute is a promise by the type's author that the type's structure and its equality agree. Programmers do not need to write the attribute in most cases, because deriving `Eq` adds it automatically. The attribute is required only when a type implements `PartialEq` by hand and wishes to allow its constants in patterns.

```rust
#[derive(PartialEq, Eq)]
struct Point {
    x: i32,
    y: i32,
}

const ORIGIN: Point = Point { x: 0, y: 0 };

match p {
    ORIGIN => { /* ... */ }
    _ => {}
}
```

In the example, the derived `Eq` implementation adds the attribute, so `ORIGIN` may be used in the pattern. A type with a hand-written equality that does not also implement `Eq` would not receive the attribute, and using its constants in patterns would be an error.

Constants of built-in types, such as integers, characters, booleans, and references to strings, are always permitted in patterns, because their equality is primitive and their structure is trivially the same.

## Reference-level explanation

The attribute `#[structural_match]` is feature-gated. It may be applied to a struct, enum, or union. When the compiler expands a constant of such a type into a pattern, it does so only if the attribute is present on the type, or on each type that appears in the constant's structure. If any such type lacks the attribute, the compiler reports an error at the use site of the constant.

The `#[derive(Eq)]` macro inserts the attribute on the type it decorates. This insertion does not require the programmer to enable the feature gate, since the derive is part of the standard library and its expansion is an implementation detail. Hand-written implementations of `Eq` do not insert the attribute.

The check applies recursively. A struct containing a field of a type that lacks the attribute cannot itself be used as a pattern constant, even if the outer type carries the attribute, because the expansion would reach the inner type. The compiler reports the first offending type it finds.

Constants whose values are primitive integers, characters, booleans, floating point numbers, and string slices are expanded without the check. Floating point numbers are a special case, since their equality is not reflexive for NaN, and the compiler has long rejected them in patterns. This RFC does not change that rule.

## Drawbacks

The restriction is a breaking change for programs that use constants of types without the attribute in patterns. The RFC argues that such programs are rare, and the compiler will report a clear message that explains how to resolve the error. Nonetheless, some crates will need updates, and the update path must be documented.

The rule adds one more concept for programmers to learn. A type that derives `Eq` can be used in patterns, but a type with a manual `PartialEq` cannot, and the reason is not obvious from the source alone.

## Rationale and alternatives

The most direct alternative is to remove the ability to use constants of struct and enum types in patterns entirely. This would be simpler, but it would remove a useful feature that many programs depend on, particularly for matching against sentinel values.

A second alternative is to require that the type implement `PartialEq` and to use the equality directly, rather than expanding the structure. This would require the compiler to call user code during pattern matching, which has implications for exhaustiveness checking and for the predictability of matches. The authors judged that this would be a larger change, with a greater risk of unexpected behavior.

A third alternative is to keep the current behavior and warn when a type's structure and equality disagree. Detecting disagreement in general is impossible, so such a lint would be incomplete, and the proposal prefers an explicit marker that the author chooses to place.

The chosen design makes the requirement explicit, preserves the common case through the derive, and gives authors a deliberate choice for hand-written implementations.

## Prior art

Several languages distinguish between types that may be matched by structure and types that require a separate equality check. The distinction is familiar to programmers who have worked with pattern matching in other systems, and the proposal adopts a version of it suited to Rust's existing rules.

## Unresolved questions

- The treatment of unions in patterns requires further study, since their structure is not directly observable in the same way.
- The diagnostic message for the error should be reviewed to ensure that it leads programmers to the correct fix.
- Whether the attribute should be stabilized as part of a broader design for pattern matching remains an open question.

## Future possibilities

If the attribute proves useful, the language may later allow authors to declare the matching behavior of their types more precisely, for example by providing a custom expansion. This RFC does not propose such a feature, but it establishes the principle that a constant in a pattern should match according to a rule the author has endorsed.
