# Rust RFC 3016: `const_ub`

- Feature Name: `const_ub`
- Start Date: 2024-05-06
- Status: Proposed

## Summary

This RFC defines the behavior of undefined behavior (UB) that occurs during compile-time function evaluation (CTFE). When UB is detected during the evaluation of a constant, the affected evaluation query produces either an unspecified result or a hard compile-time error. The effect is confined to that query. The compilation process as a whole is not infected: other constants, other items, and the code generation pipeline proceed as they would otherwise. The RFC aims to make the consequences of UB in constant contexts predictable without requiring the compiler to reason about every possible program.

## Motivation

Constant evaluation in Rust runs an interpreter over MIR. The interpreter detects many forms of undefined behavior, such as out-of-bounds memory access, reads of uninitialized memory, and invalid values for a type. Today the handling of these cases is inconsistent. In some situations the interpreter reports an error that stops compilation, while in others the problem surfaces only later, or it is treated as a bug in the compiler. Users find this difficult to reason about. A program that compiles on one day may fail on another after an unrelated change to the standard library, because a constant that previously avoided a problematic path now reaches it.

A clear rule helps in three ways. It gives library authors a definite contract to rely on when they write `const fn`. It gives the compiler team a definite target for diagnostics. It also keeps the scope of any failure small, so that one bad constant does not cause the compiler to abandon unrelated work.

## Guide-level explanation

Consider a constant whose initializer calls a `const fn` that performs an operation the interpreter cannot justify. Under this RFC, the compiler evaluates the constant and reports one of two outcomes.

The first outcome is a hard error. The error names the constant, identifies the operation that caused the undefined behavior, and points to the location in the source that triggered it. Compilation of the crate fails, but the diagnostic is produced for that constant only, and other items are still checked so that the user sees all related problems in a single run.

The second outcome is an unspecified value. In this case the compiler does not promise any particular result for the constant, and it may reject uses of the constant in certain positions. The user is not expected to rely on the value. The RFC does not allow this outcome to silently produce a result that is then used in code generation without any diagnostic.

Users who write `const fn` are encouraged to avoid undefined behavior entirely. The rule in this RFC is a safety net, not a license.

## Reference-level explanation

When the constant evaluator detects that an evaluation has reached undefined behavior, it records a failure for the query that requested the evaluation. The failure carries the kind of undefined behavior and the span of the operation that caused it. The query is marked as failed, and the failure is cached so that subsequent requests for the same constant receive the same result without repeating the evaluation.

Failure is local. The evaluator does not poison the global compilation context, and it does not mark unrelated queries as failed merely because they were scheduled after the failed one. Items that depend on the failed constant receive a secondary failure that refers to the original. This dependency tracking uses the existing query system and does not require new infrastructure.

For cases where the compiler cannot determine whether a program is well formed, the RFC allows an unspecified result. The compiler must mark the result as unspecified and must not perform optimizations that depend on a particular value. In practice this means the constant is treated as opaque by later analysis. Uses that require a known value, such as array lengths or pattern matching on constants, produce a hard error, because a value cannot be unspecified in those positions.

The RFC requires that every case of detected UB in constant evaluation be classified as either a hard error or an unspecified result. Cases that are not classified this way are considered compiler bugs. The classification is recorded in the source of the evaluator so that future additions follow the same rule.

## Drawbacks

Localizing failures means that some errors may be reported in a different order than users expect, and a single root cause may produce several diagnostics. The dependency tracking adds bookkeeping that could introduce its own bugs. The distinction between hard errors and unspecified results is subtle, and some users may be surprised that an unspecified result is accepted in some positions and rejected in others.

## Rationale and alternatives

An alternative is to make every case of UB in constant evaluation a hard error at the first point of detection. This is simple, but it causes the compiler to stop too eagerly and to report errors that are not relevant to the user's current change. It also makes it harder to add new evaluator features without fear of breaking existing programs.

A second alternative is to define the result of UB in constant evaluation as a specific value, such as zero. This would make programs more predictable, but it would also hide bugs and would require the compiler to commit to a semantics that may later conflict with the language's aims.

The approach taken here separates the question of what happens to a single constant from the question of what happens to the compilation as a whole. This separation is the central design choice of the RFC.

## Prior art

Other compilers with compile-time evaluation have faced the same issue. Several resolve it by treating the evaluation as an isolated computation whose failure does not affect the rest of the program. The design here draws on that experience and adapts it to the query architecture of the Rust compiler.

## Unresolved questions

- How should the unspecified result be displayed in diagnostics, and should it be shown at all?
- Which positions should reject unspecified results, beyond array lengths and pattern matching?
- How will the classification be checked, and can a test suite confirm that each detected case follows the rule?

## Future possibilities

If the classification proves stable, the compiler could offer a lint that flags constants whose evaluation is known to produce an unspecified result, giving users an early warning before they depend on the value. A later RFC could also refine the set of operations that the evaluator treats as undefined, in light of experience with real code.
