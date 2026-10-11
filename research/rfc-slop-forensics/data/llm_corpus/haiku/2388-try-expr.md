# RFC 2388: `try_expr`

- Feature Name: `try_expr`
- Start Date: 2017-07-18
- Tracking Issue: (to be assigned)
- Status: Proposed

## Summary

RFC 243 left the choice of keyword for `catch { .. }` expressions unresolved. This RFC settles that choice. Specifically, it:

1. reserves `try` as a keyword in edition 2018,
2. replaces `do catch { .. }` with `try { .. }`, and
3. does not reserve `catch` as a keyword.

## Motivation

Rust's error handling is built on values of types such as `Result` and `Option`, and on the `?` operator, which propagates a failure from the current function. Some code needs to propagate failure not from the whole function but from a smaller region of code. A block that computes several fallible values and handles any failure in one place is a common pattern. RFC 243 proposed a construct for this, a `catch` block, but it did not fix the spelling of the keyword that introduces it.

The original design used a `do catch` form to avoid reserving a new word. The phrase was unusual, and it was not clear whether it would be accepted by the community. Users who had written code with the experimental form found it awkward. The question of the keyword needed a decision before the feature could be stabilized, because the choice of keyword determines which identifiers become unavailable to programmers.

There are several considerations. Reserving a word breaks any existing code that uses it as an identifier, so the choice must minimize that breakage. The word must also be clear to a reader, so that the purpose of the block is apparent. The design should fit with the existing keyword set, and with the plan for editions, which allows new keywords to be introduced only in a new edition.

## Guide-level explanation

A `try` block groups a sequence of fallible operations and makes the enclosing block produce a value that reflects any failure:

```rust
let result: Result<u32, ParseError> = try {
    let a = parse_first(input)?;
    let b = parse_second(input)?;
    a + b
};
```

Within the `try` block, the `?` operator propagates failure to the end of the block rather than to the function. If any operation fails, the block evaluates to the failure, and the remaining operations are skipped. If all succeed, the block evaluates to the final expression.

The keyword `try` is reserved in edition 2018 and later. Programs written for earlier editions can continue to use `try` as an identifier, because the keyword is introduced only with the new edition. The keyword `catch` is not reserved, so existing code that uses that word as a name is unaffected.

The form `do catch { .. }`, which was used in the earlier experimental design, is replaced by `try { .. }`. Code written with the earlier form will need to be updated, but the change is mechanical and can be made with a tool.

## Reference-level explanation

The grammar introduces a `try` block expression, written as the keyword `try` followed by a block. A `try` block has the same type rules as the expression it replaces, and its value is determined by the final expression in the block or by the first failure that occurs during evaluation.

Within a `try` block, the `?` operator refers to the innermost enclosing `try` block when one exists, and otherwise to the enclosing function. This rule nests in the same way as the rules for labeled loops. The type of the failure value is determined by the expected type of the block, which is either written explicitly or inferred from the context in which the block is used.

The keyword `try` is added to the set of reserved words in the 2018 edition. In earlier editions, the word remains an ordinary identifier, and the compiler accepts the `try` block only when the feature is enabled and the edition permits it. Tools that migrate code between editions should rewrite identifiers named `try` where they would conflict.

The keyword `catch` is not reserved. The `do catch` form is removed from the experimental design, so that the spelling `do` is not needed for this construct. Any code using the experimental form must be updated.

The proposal does not change the semantics of `?` outside of `try` blocks, and it does not change how `Result` or `Option` are defined.

## Drawbacks

Reserving `try` removes a word that some programmers have used as an identifier, and this will require migration in code written for early editions. Although the migration is simple, it is a cost borne by existing users. The choice of `try` may also be confused with the `try` keywords used in other languages, which have different semantics, although the meaning of the block here is close to what the name suggests.

## Rationale and alternatives

Several alternatives were considered. The keyword `catch` was the natural choice for some, since it matches the name used in other languages. However, reserving `catch` would have broken more existing code, and it suggests exception handling that the construct does not provide. The keyword `try` is shorter and describes the intent of the block, which is to attempt a sequence of operations and handle failure.

Keeping `do catch` was also considered. It avoids reserving any word, but it is an awkward phrase that does not read naturally, and the two-word form is harder to search for and to teach.

The chosen design reserves one word, `try`, in a new edition, and it does not reserve `catch`. This balances the cost of breakage against the clarity of the resulting syntax.

## Prior art

Several languages use a block form for grouping fallible operations, and some use the name `try` for it. The experience in those languages suggests that the form is useful and that readers understand it quickly when the keyword is chosen well. The design here draws on that experience while keeping the semantics consistent with the existing `?` operator.

## Unresolved questions

- The precise interaction between `try` blocks and labeled breaks, which may need additional rules to define how a break exits a block that produces a failure.
- Whether the expected type of a `try` block should be inferred in all cases, or whether an annotation should be required when inference is ambiguous.
- The migration tooling for code that uses `try` as an identifier, and the diagnostics that should guide the programmer through it.

## Future possibilities

Future work could extend `try` blocks to support additional forms of control, such as early exit with a value other than the failure. The keyword may also be used for related constructs that group fallible operations in other ways. These extensions would be considered in their own proposals, and the keyword decision in this RFC does not depend on them.
