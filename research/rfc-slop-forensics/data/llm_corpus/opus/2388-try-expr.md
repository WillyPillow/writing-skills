- Feature Name: `try_expr`
- Start Date: 2018-04-04
- RFC PR: [rust-lang/rfcs#2388](https://github.com/rust-lang/rfcs/pull/2388)
- Rust Issue: [rust-lang/rust#50412](https://github.com/rust-lang/rust/issues/50412)

# Summary

RFC 243 left open the keyword for `catch { .. }` expressions. This RFC settles it. Specifically, it:

1. reserves `try` as a keyword in edition 2018,
2. replaces `do catch { .. }` with `try { .. }`, and
3. does **not** reserve `catch` as a keyword.

# Motivation

RFC 243 introduced the `?` operator and a block expression that limits how far `?` propagates errors. Inside such a block, a `?` that fails exits the block, not the enclosing function, and the block evaluates to the error:

```rust
let result: Result<i32, ParseIntError> = catch {
    let a = "1".parse::<i32>()?;
    let b = "2".parse::<i32>()?;
    a + b
};
```

The `?` operator was stabilized in Rust 1.13. The block expression was not, partly because its syntax was never settled. RFC 243 used `catch` as a placeholder and listed the choice of keyword as an unresolved question.

Since `catch` is not a reserved word in Rust 2015, the nightly implementation could not use bare `catch { .. }` without breaking code like:

```rust
struct catch;
let catch = 5;
```

So nightly uses `do catch { .. }`, which parses unambiguously because `do` is reserved. Nobody considers `do catch` the final syntax. It is awkward to read and write, and it reads like a loop construct in other languages.

Edition 2018 is an opportunity to reserve new keywords. If the feature is going to use a new keyword, that keyword needs to be reserved now, or the next opportunity is years away. This RFC decides which one.

# Guide-level explanation

A `try` block runs a sequence of statements in which `?` propagates only to the end of the block:

```rust
fn parse_pair(a: &str, b: &str) -> (Option<i32>, i32) {
    let sum: Result<i32, ParseIntError> = try {
        a.parse::<i32>()? + b.parse::<i32>()?
    };
    // `sum` is Ok(..) or the first Err; the function continues either way.
    ...
}
```

The final expression of the block is wrapped automatically. If the block's type is `Result<T, E>`, a final expression of type `T` becomes `Ok(value)`. If the block's type is `Option<T>`, it becomes `Some(value)`. This is sometimes called "Ok-wrapping."

`try` blocks are expressions and can be used anywhere an expression can:

```rust
let config = try { load_file(path)?.parse_config()? }
    .unwrap_or_default();
```

In edition 2015, `try` is not a keyword and `try { .. }` is not available. Code in edition 2015 can still use `r#try` to refer to identifiers named `try`, and the old `try!` macro keeps working there.

# Reference-level explanation

## Keyword reservation

`try` becomes a reserved keyword in edition 2018. Identifiers named `try` in 2018 code must be written as raw identifiers: `r#try`.

The standard library's `try!` macro remains available. In edition 2018, it must be invoked as `r#try!(..)`. The macro is already deprecated in favor of `?`, so this affects little code, and `cargo fix --edition` performs the rewrite automatically.

## Syntax

```text
TryBlockExpression :
    `try` BlockExpression
```

`try` blocks have the same restrictions as other block-like expressions with respect to statement position and struct literal ambiguity.

## Semantics

The semantics are those specified in RFC 243, with the following clarification of Ok-wrapping. Within a `try` block of type `R` where `R: Try`, the expression `?` applied to `x` desugars to:

```rust
match Try::into_result(x) {
    Ok(v) => v,
    Err(e) => break 'try_block Try::from_error(From::from(e)),
}
```

and the block's tail expression `e` becomes `Try::from_ok(e)`.

The type of a `try` block is not inferred from the tail expression alone; it must usually be known from context, such as a type annotation on the binding. Improving inference here is a separate concern.

## The `catch` identifier

`catch` is not reserved in any edition. It remains a regular identifier. The `do catch { .. }` syntax is removed from nightly.

# Drawbacks

- Programmers from Java, C++, JavaScript, and C# associate `try` with exception handling, where a `try` block is paired with `catch`. A Rust `try` block has no `catch` arm, and errors are ordinary values, not unwinding. Some confusion is likely at first.
- Reserving a keyword breaks code that uses `try` as an identifier, though editions confine this to crates that opt into 2018.

# Rationale and alternatives

## Why `try`?

`try` describes what the block does from the reader's point of view: the operations inside are *tried*, and failure is captured. That is precisely the sense in which other languages use it. The fact that Rust then handles the result with `match` or methods rather than a `catch` clause is a natural difference, not a contradiction.

`try` also already has strong associations in Rust: the `try!` macro and the `Try` trait both name exactly this kind of error propagation. Using the same word for the block that scopes `?` is consistent with existing terminology.

## Why not `catch`?

`catch` names the wrong end of the operation. In exception-based languages, the `catch` block is where you *handle* an error. Here, the block is where errors *occur*; handling happens afterward. Using `catch` for the region where errors are raised inverts its familiar meaning.

`catch` is also commonly used as an identifier, for example in testing and promise libraries, so reserving it would break more code.

## Why not reserve `catch` too, for future use?

A future `try { .. } catch e { .. }` construct has been suggested. That design does not exist yet, and reserving a keyword on the off chance it might be used would be premature. If such a feature is proposed, it can use a contextual keyword, since `catch` would only appear directly after a `try` block, where there is no ambiguity.

## Other candidates

- `do { .. }`: short, and `do` is already reserved, but it says nothing about errors and is used for loops or monadic blocks elsewhere.
- `trap`, `attempt`, `fallible`: less familiar and would be new keywords with no existing association.
- Keeping `do catch`: nobody actually likes it.

# Prior art

- Swift uses `do { try f() } catch { .. }`, with `try` marking each fallible call.
- Kotlin and Scala have `try` as an expression that yields a value.
- Haskell's `do` notation in the `Either` monad has the same semantics as a `try` block with Ok-wrapping.

# Unresolved questions

- Whether Ok-wrapping is the right behavior; this was decided in RFC 243 but remains debated, and may be revisited before stabilization.
- Type inference improvements for `try` blocks.
