# RFC 2388: try_expr

- Feature Name: `try_expr`
- Start Date: 2018-03-29
- RFC PR: rust-lang/rfcs#2388
- Rust Issue: rust-lang/rust#50412

## Summary

RFC 243 left the choice of keyword for `catch { .. }` expressions unresolved. This RFC settles the choice of keyword. Namely, it:

1. reserves `try` as a keyword in edition 2018.
2. replaces `do catch { .. }` with `try { .. }`.
3. does **not** reserve `catch` as a keyword.

## Motivation

The `?` operator allows early return from a function when an expression evaluates to an error. It is a concise way to propagate failures:

```rust
fn read_config(path: &Path) -> io::Result<Config> {
    let text = fs::read_to_string(path)?;
    let config = parse(&text)?;
    Ok(config)
}
```

The operator always returns from the enclosing function. Sometimes that is not what is wanted. A programmer may want to run several fallible steps, collect the first error, and handle it locally without introducing a new function or closure:

```rust
let result: Result<_, io::Error> = try {
    let a = step_one()?;
    let b = step_two(a)?;
    step_three(b)?
};
```

Here `?` exits the `try` block rather than the function, and the value of the block is either the final expression wrapped in `Ok`, or the error that was propagated. Today, the same effect is obtained with an immediately invoked closure, `(|| { ... })()`, which has several problems. A closure body cannot use `return`, `break` or `continue` to affect the outer function. It introduces a new borrow scope that complicates the capture of variables. It requires type annotations for the return type that are often hard to write, because `?` desugars through `From` and so leaves the error type ambiguous. And it is visually noisy.

RFC 243 introduced the concept of a `catch` block, which was implemented on nightly in the form `do catch { .. }`. The `do` prefix was a placeholder to avoid taking a new keyword. That RFC deferred the choice of the real syntax. Years of experimentation have shown the feature to be valuable, and it is now time to decide so that the keyword can be reserved in time for edition 2018. If a keyword is not reserved at an edition boundary, it cannot be added later without breaking existing code that uses the word as an identifier.

## Guide-level explanation

The expression `try { ... }` evaluates its block and produces a value of a type that implements `Try`. In the current design, this is typically `Result<T, E>` or `Option<T>`.

Inside the block, the `?` operator short-circuits out of the block rather than out of the function. The final expression of the block is wrapped by the appropriate success constructor, so there is no need to write `Ok(...)` on the tail.

```rust
fn parse_pair(s: &str) -> Option<(i32, i32)> {
    let pair: Option<(i32, i32)> = try {
        let mut parts = s.split(',');
        let a = parts.next()?.trim().parse().ok()?;
        let b = parts.next()?.trim().parse().ok()?;
        (a, b)
    };
    pair
}
```

A `try` block may be used anywhere an expression is accepted, including as an initializer, a function argument, or in a `match` scrutinee.

The type of a `try` block is, in general, inferred from context. If the context does not determine it, the user must annotate it, as in the first example. This is because the `?` operator is generic over the error conversion and the `Try` type, so there are many possible outcomes.

Since `try` becomes a keyword, it can no longer be used as an identifier. Code using `try` as an identifier will continue to compile in edition 2015, and in edition 2018 it must be written as a raw identifier, `r#try`. The `try!` macro, which predates `?`, uses this name and is affected. In edition 2018 it must be invoked as `r#try!(...)`, which is the only change. Automatic migration is provided by `cargo fix`.

## Reference-level explanation

### Reservation

In edition 2018 and later, `try` is a reserved keyword. The lexer treats `try` as a keyword token, which makes any use as an identifier a syntax error, with a note suggesting the raw-identifier form. In edition 2015, `try` is not reserved, and the `try` block syntax is not available except under a nightly feature gate that is specific to the edition.

### Syntax

The grammar for expressions gains a production:

```
TryBlockExpression : try BlockExpression
```

`try` is followed immediately by a block. A `try` block is a block expression and has the same restrictions on position that apply to other block-like expressions. As a statement it must be followed by a semicolon if the result is used and need not be if the type is `()`.

### Semantics

A `try` block is desugared roughly as follows:

```rust
try { <stmts>; <expr> }
// becomes
{
    let _result = 'try_block: {
        <stmts with `?` redirected to 'try_block>
        Try::from_ok(<expr>)
    };
    _result
}
```

The actual lowering uses `Try::into_result` on the operand of each `?` and `Try::from_error` on the residual, as in the existing desugaring of `?`, but with `return` replaced by a break out of the block. The details of `Try` are left to a separate RFC; this document concerns the keyword and surface syntax only.

`return`, `break` and `continue` inside a `try` block have their ordinary meaning with respect to the enclosing function or loop. They do not apply to the block. In this respect `try` blocks differ from closures. The `?` operator is the only construct that targets the block.

### What is not changed

This RFC does not alter the definition of the `Try` trait or decide whether `try` blocks wrap the tail expression automatically (the "Ok-wrapping" question). The existing behaviour on nightly, which wraps, is retained. Those questions can be revisited without a keyword change.

### The `catch` keyword

This RFC explicitly does not reserve `catch`. The earlier proposals used `catch` because it is familiar from languages with exceptions. But the semantics of the construct here are different: it does not catch an exception, it delimits where `?` returns to. It also does not catch panics. Choosing `catch` could mislead people into thinking it interoperates with `panic!` and unwinding. Moreover, `catch` is a plausible identifier in existing code, for example as a method name, and reserving it would break more code than reserving `try` would.

## Drawbacks

Reserving `try` breaks the `try!` macro in edition 2018, as well as any code that uses `try` as an identifier. The `try!` macro has been deprecated since Rust 1.39-era discussions and the `?` operator has superseded it. The raw identifier syntax `r#try!` is a workable if ugly migration, and `cargo fix` will perform it. The volume of affected code on crates.io is small.

Another drawback is that the name `try` is associated by many programmers with exception handling, so some will expect that `try` has a matching `catch`. The documentation should address this directly.

Finally, a new keyword increases the surface area of the language slightly, and to the extent that some functionality could be achieved with closures or helper functions, this is syntactic sugar.

## Rationale and alternatives

**`do catch { .. }`.** This avoids a new keyword, but it is clumsy and was always intended as a placeholder. It does not generalise to other uses of `do`.

**`catch { .. }`.** Discussed above. Its association with exception semantics is potentially misleading, and `catch` is a common identifier.

**`try { .. } catch { .. }`.** Complete exception-style syntax was considered, but it would introduce a second way to handle errors alongside `match` on `Result`. Pattern matching on the result of a `try` block is already possible and fits the language.

**`result { .. }`, `fallible { .. }`, `attempt { .. }`.** Other names were proposed but none had broad support. The keyword `try` is short, and appears in `try!`, `try_from`, `try_into` and `?`, which are all part of the same conceptual family, making it consistent with existing Rust terminology.

**Do nothing.** Leaving the feature on nightly under a placeholder would mean that users cannot depend on it and that the window to reserve a keyword in edition 2018 closes, delaying the feature until edition 2021 at best.

## Prior art

Haskell's `do` notation with `Maybe` and `Either` plays a similar role to `try` blocks combined with `?`. Swift uses `do { try ... } catch { ... }`, with `try` marking a throwing call rather than a block. Kotlin has `runCatching { ... }` as a library function. C# and Java use `try` with `catch` for exceptions, which is the association this RFC acknowledges as a drawback. Zig has `try expr` as a prefix operator, equivalent to Rust's `?`.

## Unresolved questions

* Should `try` blocks wrap the tail expression automatically, or require an explicit `Ok(...)`? This RFC defers the question.
* How should type inference for `try` blocks be improved so that fewer annotations are needed?
* Should `try fn` or `try` as a modifier be reserved for future use? Reserving the keyword leaves the door open.
