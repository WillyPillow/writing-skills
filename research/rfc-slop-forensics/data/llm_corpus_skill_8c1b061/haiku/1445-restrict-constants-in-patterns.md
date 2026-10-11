# Rust RFC 1445: structural_match

## Summary

This RFC narrows the semantics that the compiler currently applies to constants in patterns. It does so without breaking, or at least without breaking much of, the code that already compiles. The RFC makes three changes. It introduces a feature-gated attribute, `#[structural_match]`, that a struct or enum can carry to show that its constants may be used in patterns. It makes `#[derive(Eq)]` apply that attribute automatically to the type it decorates, and such automatically inserted attributes do not require the feature gate. And it requires that a constant of struct or enum type expanded into a pattern must carry the attribute. Constants of built-in types are always expanded. [TODO: confirm the exact wording of the practical effect, which the material leaves incomplete.]

## Motivation

The compiler currently accepts a broader set of constants in patterns than the language designers intended. [TODO: give one example of a constant that matches today but was not meant to, and state where the intended rule is written down, if it is.]

The obstacle is that the broader semantics cannot be removed simply. A type whose constants appear in patterns today would stop compiling if the rule were tightened in one step. [TODO: estimate how much code depends on the broader rule, with the source of the estimate. Without it, the claim that the RFC avoids breakage should be narrowed to what the author can show.]

The RFC therefore aims to restrict the semantics while keeping existing code compiling in the common case. The aim is stated as a goal, not as a result, because the material does not contain a measured breakage count. [TODO: give the measured count, or state that none was taken.]

## Guide-Level Explanation

A type that should allow its constants to appear in patterns carries the attribute `#[structural_match]`. A type that derives `Eq` receives the attribute without writing it, because the derive adds it.

[TODO: give an example of a struct with a constant used in a pattern, before and after the change. The example is not in the material.]

[TODO: give the error a writer sees when a constant of a type without the attribute appears in a pattern. The message text is not in the material.]

## Reference-Level Explanation

When the compiler expands a constant of struct or enum type into an equivalent pattern, it checks for the attribute. If the attribute is missing, the expansion is refused. Constants of built-in types are expanded with no check. [TODO: state the exact check, including how it treats generic types and types from other crates.]

The automatic insertion by `#[derive(Eq)]` is not gated behind the feature. [TODO: state how this interacts with stable and nightly compilers, and whether the feature gate covers the explicit attribute only.]

## Drawbacks

The change prevents some patterns that compile today. [TODO: state which patterns, and how a writer can rewrite each one.]

A type that does not derive `Eq` must add the attribute by hand, which adds one more thing to learn. [TODO: state whether the author has seen this burden in practice.]

## Rationale and Alternatives

The central tension is between tightening the semantics and keeping existing code working. The RFC tries to resolve it by making the new rule depend on the attribute, and by inserting the attribute automatically for the common case of `Eq`. [TODO: state which of these two mechanisms the deciding reason depends on.]

The alternative of making every constant expansion fail is not considered in the material. [TODO: state whether this alternative was considered, and why it lost.]

Another alternative is to keep the broader semantics and document them. [TODO: state whether this was considered, and the reason it lost.]

## Unresolved Questions

[TODO: list the open questions. Candidates include the exact scope of the feature gate, the treatment of generic types, and the migration path for the patterns that the restriction rejects.]
