# RFC 1445: structural_match

## Summary

The current compiler gives pattern matching a wider meaning than was originally intended. This RFC adds three mechanisms that narrow that meaning while breaking little, if any, existing code.

1. A feature-gated attribute `#[structural_match]` that can be applied to a struct or enum `T`. It states that constants of type `T` can be used within patterns.
2. A rule that `#[derive(Eq)]` applies this attribute to the struct or enum it decorates. Automatically inserted attributes do not need the feature gate.
3. A rule that, when the compiler expands a constant of struct or enum type into an equivalent pattern, the type must carry `#[structural_match]`. Constants of builtin types are always expanded.

The practical effect is to prevent the use of constants in patterns [TODO: the abstract is cut off here. Complete the sentence: which constants stop working, and under what condition.]

## Motivation

A `match` arm can contain a constant in place of a literal. The compiler currently turns the constant into the pattern it stands for, by expanding its value field by field. [TODO: confirm this description of the current implementation against the compiler source. The material says only that the semantics are "more expansive" than intended.]

The RFC asserts that this expansion goes further than the language design meant. The reader needs the intended meaning, the actual meaning and a case where they differ. [TODO: give one concrete program. It should have a user-defined type, a constant of that type, and a `match` on it, where the compiler's expansion produces a result that differs from what a programmer would expect from the type's equality operation. State the expected and the actual result.]

The likely source of the difference is the relationship between a pattern match and an equality test. A pattern match compares structure. A user-defined `PartialEq` can compare something else. When a constant is used in a pattern, a programmer may reasonably expect the pattern to behave like `==` on that type. If the compiler instead compares structure, the two can disagree. [TODO: this paragraph is the drafting assistant's reconstruction of the problem from the title and the derive rule. The author to confirm it is the problem the RFC addresses, or to replace it.]

## Detailed design

### The attribute

`#[structural_match]` may be applied to a struct or an enum `T`. Its meaning is: constants of type `T` may be used within patterns, because matching against such a constant is equivalent to matching against its structure. [TODO: state the condition on `T` under which the attribute is sound. A plausible condition is that every field also has a type for which structural matching is allowed, and that `T`'s equality agrees with structural comparison; the author must say what the compiler checks and what it leaves to the programmer.]

The attribute is behind a feature gate. A crate must enable the gate to write the attribute by hand. [TODO: name the gate.]

### The derive rule

`#[derive(Eq)]` adds `#[structural_match]` to the type it decorates. The attribute that the derive inserts does not need the feature gate.

The choice of `Eq`, not `PartialEq`, is a decision that needs a reason. [TODO: the author to explain. A reader will ask why deriving the weaker trait does not suffice, and what is the situation for floating-point types, which have `PartialEq` and not `Eq`.]

### Expansion of constants

When the compiler expands a constant of struct or enum type into a pattern, it requires that the type carries the attribute. If it does not, expansion is an error. [TODO: give the error text, or the intended shape of it, and say whether it is a hard error at once or a warning first.]

Constants of builtin types are always expanded. [TODO: list which types are builtin for this purpose. Say how references, slices, arrays and tuples are treated.]

### Worked example

```rust
#[derive(PartialEq, Eq)]
struct Point { x: i32, y: i32 }

const ORIGIN: Point = Point { x: 0, y: 0 };

fn is_origin(p: Point) -> bool {
    match p {
        ORIGIN => true,
        _ => false,
    }
}
```

`Point` derives `Eq`, so it receives `#[structural_match]`, and the constant `ORIGIN` expands into the pattern `Point { x: 0, y: 0 }`. This program is accepted before and after the RFC.

A type that implements `PartialEq` by hand and does not derive `Eq` has no attribute. A constant of that type in a pattern is rejected after the RFC. [TODO: replace this paragraph with a second code example, including the compiler's message, once the error form is fixed.]

## Drawbacks

The RFC says it breaks "much, if any" existing code in the negative: it aims to break little or nothing. The material gives no measurement of how much code is affected. [TODO: report the result of building a named set of crates, for example the compiler's own test suite and a stated number of published crates, with the compiler modified to reject the non-attributed cases. Give the count of failures. If this was not done, the RFC must say so and must not claim that breakage is rare.]

Known costs, from the design itself:

- A type that implements `PartialEq` by hand, and whose constants appear in patterns today, stops compiling. The programmer has to rewrite the match, for example by using a guard with `==`.
- The attribute adds a new concept to the language, and a feature gate to track. [TODO: state when the gate is intended to be removed or stabilized.]

## Alternatives

The material does not say what else was considered. The following are suggestions for the author to evaluate, not rejected options.

- Keep the current semantics and document them. This costs nothing in compatibility and leaves the mismatch with `==`.
- Reject all constants of user-defined type in patterns. This is simpler to specify and breaks more code.
- Make the compiler call `PartialEq::eq` for constants in patterns. [TODO: the author to say whether this is possible, given that patterns need to be checked for exhaustiveness at compile time.]

[TODO: for each alternative the author considered, give the specific goal that made it lose.]

## Reversibility

The attribute is feature-gated, which limits the commitment while the design is tested. The derive rule is harder to reverse: once the derive inserts the attribute, programs that rely on it exist. [TODO: author to confirm and to say what happens to the derive rule if the gate is removed.]

## Unresolved questions

- The completion of the "practical effect" sentence in the Summary.
- Why `Eq` and not `PartialEq`.
- The treatment of generics: whether a generic type's attribute depends on its parameters.
- The treatment of references and nested types inside a constant.
- The release schedule for turning the check from permitted to enforced.

## Migration

[TODO: give the steps for a crate author whose code fails after the change, and say whether a lint, in place of an error, runs for one release first. The material does not give a schedule.]
